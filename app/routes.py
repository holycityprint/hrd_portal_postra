# ==============================================================
#  app/routes.py – Blueprint utama untuk Dashboard HR Portal
# ==============================================================

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import date
from sqlalchemy import func, literal
from app.models import Employee, Client, Assignment, Attendance, User

# 🔹 Inisialisasi Blueprint utama
main_bp = Blueprint('main', __name__)

# -------------------------------------------------------------
# 🏠  DASHBOARD UTAMA
# -------------------------------------------------------------
@main_bp.route('/')
@login_required
def dashboard():
    """Dashboard utama dengan visualisasi data lintas modul."""
    from app import db
    today = date.today()

    # ---- Angka ringkasan utama ----
    total_employees = Employee.query.count()
    active_employees = Employee.query.filter_by(status='aktif').count()
    total_clients = Client.query.count()
    total_assignments = Assignment.query.filter_by(status='aktif').count()
    total_karyawan = User.query.filter_by(role='employee').count()

    # ============================================================
    # JUMLAH HADIR HARI INI
    #   gunakan kolom Attendance.date dan trim/lower status
    # ============================================================
    hadir_hari_ini = Attendance.query.filter(
        Attendance.date == today,
        func.trim(func.lower(Attendance.status)) == literal('hadir')
    ).count()

    # ============================================================
    # GRAFIK 1 — STATUS KARYAWAN (tabel Employee)
    # ============================================================
    emp_status = (
        db.session.query(Employee.status, func.count(Employee.id))
        .group_by(Employee.status)
        .all()
    )
    status_labels = [s[0].capitalize() for s in emp_status] if emp_status else []
    status_counts = [s[1] for s in emp_status] if emp_status else []

    # ============================================================
    # GRAFIK 2 — ABSENSI HARI INI (tabel Attendance)
    #   Aman dari variasi huruf/spasi pada status
    # ============================================================
    att_labels = ['Hadir', 'Izin', 'Sakit', 'Alpha']
    att_counts = [
        Attendance.query.filter(
            Attendance.date == today,
            func.trim(func.lower(Attendance.status)) == literal('hadir')
        ).count(),
        Attendance.query.filter(
            Attendance.date == today,
            func.trim(func.lower(Attendance.status)) == literal('izin')
        ).count(),
        Attendance.query.filter(
            Attendance.date == today,
            func.trim(func.lower(Attendance.status)) == literal('sakit')
        ).count(),
        Attendance.query.filter(
            Attendance.date == today,
            func.trim(func.lower(Attendance.status)) == literal('alpha')
        ).count(),
    ]

    # ------------------------------------------------------------
    # Debugging – tampilkan data di terminal
    # ------------------------------------------------------------
    print("=" * 80)
    print("DEBUG — status_labels:", status_labels)
    print("DEBUG — status_counts:", status_counts)
    print("DEBUG — att_labels:", att_labels)
    print("DEBUG — att_counts:", att_counts)
    print("=" * 80)

    # ------------------------------------------------------------
    # Render template dashboard.html
    # ------------------------------------------------------------
    return render_template(
        'dashboard.html',
        title='Dashboard - HR Portal',
        user=current_user,
        today=today,
        total_employees=total_employees,
        active_employees=active_employees,
        total_clients=total_clients,
        total_assignments=total_assignments,
        total_karyawan=total_karyawan,
        hadir_hari_ini=hadir_hari_ini,
        status_labels=status_labels,
        status_counts=status_counts,
        att_labels=att_labels,
        att_counts=att_counts
    )