# ============================================================
# Tambahan untuk memastikan Flask tidak error saat import employee_bp
# ============================================================
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import os, uuid
from datetime import date, datetime
from flask_login import login_required, current_user
from app import db
from app.models import Employee, Attendance, ActivityLog, Client, Assignment
from app.role_check import role_required

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/employee/check')
def employee_check():
    """Dummy route agar import blueprint employee_bp valid dan aman."""
    return "✅ Blueprint employee_bp aktif (dummy route)."


# ============================================================
# 👤 DASHBOARD KARYAWAN
# ============================================================
@employee_bp.route('/dashboard_employee', methods=['GET', 'POST'])
@login_required
@role_required('employee')
def dashboard_employee():
    """Dashboard utama bagi karyawan."""
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash("⚠️ Data karyawan tidak ditemukan untuk akun ini.", "warning")
        return redirect(url_for("auth.logout"))

    today = date.today()
    attendance_today = Attendance.query.filter_by(
        employee_id=employee.id, date=today
    ).first()

    return render_template(
        "employee/dashboard_employee.html",
        employee=employee,
        today=today,
        attendance_today=attendance_today,
    )


# ============================================================
# 📝 UPLOAD AKTIVITAS HARIAN (foto + lokasi realtime)
# ============================================================
@employee_bp.route('/upload_activity', methods=['POST'])
@login_required
@role_required('employee')
def upload_activity():
    """Terima form aktivitas dari dashboard karyawan (foto + GPS)."""
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash("⚠️ Data karyawan tidak ditemukan.", "warning")
        return redirect(url_for("auth.logout"))

    description = request.form.get('description')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    file = request.files.get('photo')

    # Simpan foto aktivitas
    filename = None
    if file and file.filename:
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'activity_photos')
        os.makedirs(upload_folder, exist_ok=True)
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{employee.id}_{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(upload_folder, filename))

    # Buat record aktivitas baru
    new_log = ActivityLog(
        employee_id=employee.id,
        description=description,
        latitude=latitude,
        longitude=longitude,
        image=filename,                  # pastikan kolom di model ActivityLog bernama 'image'
        created_at=datetime.now()
    )
    db.session.add(new_log)
    db.session.commit()

    flash("✅ Aktivitas harian berhasil disimpan.", "success")
    return redirect(url_for("employee.dashboard_employee"))


# ============================================================
# ⚙️ PEMROSES ABSENSI KARYAWAN
# ============================================================
@employee_bp.route('/do_attendance', methods=['POST'])
@login_required
@role_required('employee')
def do_attendance():
    """Tangani tombol Clock In / Clock Out dari dashboard_employee."""
    today = date.today()
    employee = Employee.query.filter_by(user_id=current_user.id).first()

    if not employee:
        flash("⚠️ Data karyawan tidak ditemukan.", "warning")
        return redirect(url_for("auth.logout"))

    attendance = Attendance.query.filter_by(employee_id=employee.id, date=today).first()
    action = request.form.get('action')
    current_time = datetime.now().time()

    if not attendance:
        attendance = Attendance(employee_id=employee.id, date=today, status='hadir')
        db.session.add(attendance)
        db.session.commit()

    if action == 'clock_in' and not attendance.check_in:
        attendance.check_in = current_time
        flash('✅ Absen masuk berhasil!', 'success')
    elif action == 'clock_out' and not attendance.check_out:
        attendance.check_out = current_time
        flash('👋 Absen pulang berhasil!', 'info')

    db.session.commit()
    return redirect(url_for('employee.dashboard_employee'))


# ============================================================
# ✅ OPSIONAL: KEAMANAN TAMBAHAN
# ============================================================
from functools import wraps

def ensure_employee_exists(func):
    """Pastikan akun login memiliki record Employee di DB."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        emp = Employee.query.filter_by(user_id=current_user.id).first()
        if not emp:
            flash("⚠️ Akun ini belum terhubung dengan data karyawan.", "warning")
            return redirect(url_for("auth.logout"))
        return func(*args, **kwargs)
    return wrapper

# Terapkan jika fungsi sudah didefinisikan
if "dashboard_employee" in globals():
    dashboard_employee = ensure_employee_exists(dashboard_employee)
if "upload_activity" in globals():
    upload_activity = ensure_employee_exists(upload_activity)
if "do_attendance" in globals():
    do_attendance = ensure_employee_exists(do_attendance)

import logging
logging.basicConfig(level=logging.INFO)
logging.info("✅ employee/routes.py loaded successfully")