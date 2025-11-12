from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
import os

# ==========================================================
# 🧩  Inisialisasi global objek database & login manager
# ==========================================================
db = SQLAlchemy()
login_manager = LoginManager()

# --- Konfigurasi default Flask-Login ---
login_manager.login_view = "auth.login"
login_manager.login_message = "Silakan login terlebih dahulu untuk mengakses halaman ini."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    """Dipanggil oleh Flask-Login untuk memuat user aktif berdasarkan ID."""
    from app.models import User  # Menghindari circular import
    return User.query.get(int(user_id))


# ==========================================================
# 🏗️  Factory Function : membuat & mengonfigurasi Flask App
# ==========================================================
def create_app():
    app = Flask(__name__)

    # -------------------- Konfigurasi dasar --------------------
    app.config["SECRET_KEY"] = "kuncirahasia_superaman"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hrd_portal.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # -------------------- Konfigurasi tambahan untuk login mobile --------------------
    # Pastikan cookie dikirim juga di browser HP (terutama Chrome/Safari)
    app.config["SESSION_COOKIE_SECURE"] = True           # wajib True untuk HTTPS (Render)
    app.config["SESSION_COOKIE_SAMESITE"] = "None"       # agar cookie tidak diblokir mobile browser
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SECURE"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "None"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True

    # 🔧 tambahan opsional — beberapa browser mobile perlu nama domain eksplisit
    app.config["SESSION_COOKIE_DOMAIN"] = None  # biarkan Flask isi otomatis agar sesuai domain render

    # Folder upload + batas ukuran file upload
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # Maks 5 MB

    # Inisialisasi ekstensi
    db.init_app(app)
    login_manager.init_app(app)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ==========================================================
    # 🌐 CORS diaktifkan penuh untuk dukung login via HP
    # ==========================================================
    CORS(
        app,
        supports_credentials=True,
        origins=["*"],  # izinkan akses dari semua domain (Render, localhost, HP)
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # ==========================================================
    # 🔹 REGISTRASI BLUEPRINTS
    # ==========================================================
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.hr.routes import hr_bp
    app.register_blueprint(hr_bp, url_prefix="/hr")

    try:
        from app.client.routes import client_bp
        app.register_blueprint(client_bp, url_prefix="/client")
        print("✅ Blueprint client berhasil diregistrasi.")
    except Exception as e:
        print(f"⚠️  Gagal memuat blueprint Client: {e}")

    from app.employee.routes import employee_bp
    app.register_blueprint(employee_bp, url_prefix="/employee")

    try:
        from app.employee.routes_input import employee_input_bp
        app.register_blueprint(employee_input_bp, url_prefix="/employee/input")
    except ModuleNotFoundError:
        print("ℹ️ Modul input data karyawan belum tersedia, dilewati sementara.")

    try:
        from app.admin.routes import admin_bp
        app.register_blueprint(admin_bp, url_prefix="/admin")
    except ModuleNotFoundError:
        pass

    # ==========================================================
    # 🔹 ERROR HANDLER UMUM
    # ==========================================================
    @app.errorhandler(404)
    def not_found_error(error):
        return (
            "<h3 style='text-align:center;margin-top:40px'>"
            "Halaman tidak ditemukan (404)</h3>",
            404,
        )

    @app.errorhandler(401)
    def unauthorized_error(error):
        return (
            "<h3 style='text-align:center;margin-top:40px'>"
            "Anda belum login atau tidak memiliki izin (401)</h3>",
            401,
        )

    @app.errorhandler(500)
    def internal_error(error):
        return (
            "<h3 style='text-align:center;margin-top:40px'>"
            "Terjadi kesalahan pada server (500)</h3>",
            500,
        )

    # ==========================================================
    # 🔹 INISIALISASI AKUN DEFAULT
    # ==========================================================
    with app.app_context():
        try:
            init_default_accounts()
        except Exception as e:
            print(f"ℹ️  Tidak dapat membuat akun default: {e}")

    return app


# ==========================================================
# ✅ Membuat akun default admin, employee, dan client secara aman
# ==========================================================
def init_default_accounts():
    """Membuat akun default admin, employee, dan client secara otomatis."""
    from app.models import User
    from sqlalchemy.exc import OperationalError

    try:
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", role="admin", active=True)
            admin.set_password("admin123")
            db.session.add(admin)

        employee = User.query.filter_by(username="employee").first()
        if not employee:
            employee = User(username="employee", role="employee", active=True)
            employee.set_password("employee123")
            db.session.add(employee)

        client_user = User.query.filter_by(username="client").first()
        if not client_user:
            client_user = User(username="client", role="client", active=True)
            client_user.set_password("client123")
            db.session.add(client_user)

        db.session.commit()
        print("✅ Default users initialized (admin / employee / client).")

    except OperationalError:
        print("ℹ️  Database belum siap, akun default dilewati sementara.")
