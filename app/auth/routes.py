from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
# ✅ Import Form yang baru dibuat (Wajib ada agar tidak Error 500)
from app.auth.forms import LoginForm 

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

    # ✅ Inisialisasi Form (SOLUSI ERROR 500)
    form = LoginForm()

    # ✅ Ganti "if request.method == 'POST'" dengan validasi form otomatis
    # validate_on_submit() otomatis mengecek CSRF token agar aman di HP/Render
    if form.validate_on_submit():
        
        # Ambil data dari form dan bersihkan spasi (Logic stripping kamu tetap dipakai)
        username = form.username.data.strip()
        password = form.password.data.strip()

        user = User.query.filter_by(username=username).first()

        # --- LOGIKA PENGECEKAN ---
        if not user:
            flash('❌ Username tidak ditemukan.', 'danger')
            # PENTING: Kirim form=form agar HTML tidak crash saat reload
            return render_template('auth/login.html', form=form)

        if not user.check_password(password):
            flash('❌ Password salah.', 'danger')
            return render_template('auth/login.html', form=form)

        if not user.active:
            flash('⚠️ Akun ini tidak aktif.', 'warning')
            return render_template('auth/login.html', form=form)

        # --- JIKA SUKSES ---
        login_user(user) 
        flash(f'✅ Selamat datang, {user.username}!', 'success')
        
        # Cek apakah ada parameter 'next' dari URL
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        return redirect_user_by_role(user)

    # Jika ada error validasi (misal token expired), tampilkan flash message
    if form.errors:
        for err in form.errors.values():
            flash(f'⚠️ {err[0]}', 'danger')

    # GET REQUEST (Saat halaman dibuka pertama kali)
    # ✅ Kirim variable form=form ke HTML (SOLUSI ERROR 500)
    return render_template('auth/login.html', form=form)


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
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard_admin'))
    elif user.role == 'hr':
        return redirect(url_for('hr.dashboard_hr'))
    elif user.role == 'client':
        return redirect(url_for('client.dashboard_client'))
    elif user.role == 'employee':
        return redirect(url_for('employee.dashboard_employee'))
    else:
        flash('⚠️ Role pengguna tidak dikenali.', 'warning')
        return redirect(url_for('auth.login'))