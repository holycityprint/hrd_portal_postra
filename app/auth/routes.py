from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.role_check import role_required # Asumsi ini masih digunakan

# ======================================================
# 🔐 Blueprint AUTH – Login & Logout
# ======================================================
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ------------------------------------------------------
# 🔑 LOGIN PAGE
# ------------------------------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Jika sudah login, langsung arahkan sesuai role
    if current_user.is_authenticated:
        return redirect_user_by_role(current_user)

    if request.method == 'POST':
        # >>> PERUBAHAN KRITIS: Hapus spasi di awal/akhir input
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        # <<< AKHIR PERUBAHAN KRITIS

        user = User.query.filter_by(username=username).first()

        if not user:
            # Menggunakan username yang sudah di-strip untuk pengecekan
            flash('❌ Username tidak ditemukan.', 'danger')
            return render_template('auth/login.html')

        # Membandingkan password yang sudah di-strip
        if not user.check_password(password):
            flash('❌ Password salah.', 'danger')
            return render_template('auth/login.html')

        if not user.active:
            flash('⚠️ Akun ini tidak aktif.', 'warning')
            return render_template('auth/login.html')

        # Login berhasil
        # Parameter 'remember' bisa ditambahkan di sini jika ada checkbox di form
        login_user(user) 
        flash(f'✅ Selamat datang, {user.username}!', 'success')
        
        # Cek apakah ada parameter 'next' dari URL, jika tidak, gunakan role redirect
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        return redirect_user_by_role(user)

    # GET → tampilkan halaman login
    return render_template('auth/login.html')


# ------------------------------------------------------
# 🚪 LOGOUT
# ------------------------------------------------------
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('👋 Anda telah logout.', 'info')
    return redirect(url_for('auth.login'))


# ------------------------------------------------------
# 🔄 Fungsi bantu untuk redirect berdasar ROLE
# ------------------------------------------------------
def redirect_user_by_role(user):
    """Arahkan user ke dashboard sesuai role-nya."""
    # Pastikan nama endpoint (seperti 'admin.dashboard_admin') sesuai dengan yang ada di routes Anda.
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard_admin'))
    elif user.role == 'hr':
        return redirect(url_for('hr.dashboard_hr'))
    elif user.role == 'client':
        return redirect(url_for('client.dashboard_client'))
    elif user.role == 'employee':
        # Karyawan diarahkan ke dashboard employee di blueprint 'employee'
        return redirect(url_for('employee.dashboard_employee'))
    else:
        flash('⚠️ Role pengguna tidak dikenali.', 'warning')
        return redirect(url_for('auth.login'))