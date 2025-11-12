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
    from app.models import User  # Hindari circular import
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

    # ==========================================================
    # 🔐 Konfigurasi Session agar login bekerja di HP & HTTPS
    # ==========================================================
    app.config.update(
        SESSION_COOKIE_SECURE=True,            # Cookie hanya dikirim via HTTPS
        SESSION_COOKIE_SAMESITE="None",        # Diperlukan agar cookie lintas domain bisa diterima
        SESSION_COOKIE_HTTPONLY=True,          # Lindungi cookie dari akses JS
        REMEMBER_COOKIE_SECURE=True,
        REMEMBER_COOKIE_SAMESITE="None",
        REMEMBER_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_DOMAIN=".onrender.com", # 🔄 PERUBAHAN 1: Domain pattern untuk subdomains
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7,  # 7 hari login aktif
        SESSION_PROTECTION="strong",           # Hindari invalid session di HP
        SESSION_REFRESH_EACH_REQUEST=True      # 🔄 PERUBAHAN 2: Refresh session tiap request
    )

    # Folder upload + batas ukuran file upload
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # Maks 5 MB

    # Inisialisasi ekstensi
    db.init_app(app)
    login_manager.init_app(app)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ==========================================================
    # 🌐 CORS — Konfigurasi diperbaiki untuk mobile
    # ==========================================================
    CORS(
        app,
        supports_credentials=True,
        resources={r"/*": {"origins": [
            "https://hrd-portal-postra.onrender.com",  # domain render kamu
            "http://localhost:5000",                   # untuk testing lokal
            "http://127.0.0.1:5000"                    # 🔄 PERUBAHAN 3: Tambah localhost IP
        ]}},
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],  # 🔄 PERUBAHAN 4: Tambah Accept header
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # 🔄 PERUBAHAN 5: Tambah PATCH method
        expose_headers=["Content-Type", "Authorization"]  # 🔄 PERUBAHAN 6: Expose headers untuk mobile
    )

    # ==========================================================
    # 🔄 PERUBAHAN 7: Tambahkan middleware untuk handle preflight
    # ==========================================================
    @app.after_request
    def after_request(response):
        """Middleware untuk handle CORS preflight dan security headers"""
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS,PATCH')
        response.headers.add('Access-Control-Max-Age', '600')
        return response

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
    # 🔄 PERUBAHAN 8: Tambahkan debug endpoint untuk mobile
    # ==========================================================
    @app.route('/api/debug/mobile-session')
    def debug_mobile_session():
        """Endpoint untuk debug session di mobile"""
        from flask import session, request
        import json
        debug_info = {
            'session_keys': list(session.keys()),
            'user_agent': request.headers.get('User-Agent', ''),
            'origin': request.headers.get('Origin', ''),
            'has_cookies': bool(request.cookies),
            'mobile_compatible': True
        }
        return json.dumps(debug_info)

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