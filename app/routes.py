# ==============================================================
#  app/routes.py – Blueprint utama untuk Dashboard HR Portal
# ==============================================================

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import date
from app.models import Employee, Client, Assignment, Attendance

# 🔹 Inisialisasi Blueprint utama
main_bp = Blueprint('main', __name__)

# -------------------------------------------------------------
# 🏠  DASHBOARD UTAMA
# -------------------------------------------------------------
@main_bp.route('/')
@login_required
def dashboard():
    """Menampilkan ringkasan data dari seluruh modul HR."""
    total_employees = Employee.query.count()
    active_employees = Employee.query.filter_by(status='aktif').count()
    total_clients = Client.query.count()
    total_assignments = Assignment.query.filter_by(status='aktif').count()
    today = date.today()
    hadir_hari_ini = Attendance.query.filter_by(date=today, status='hadir').count()

    return render_template(
        'dashboard.html',
        title='Dashboard - HR Portal',
        user=current_user,
        total_employees=total_employees,
        active_employees=active_employees,
        total_clients=total_clients,
        total_assignments=total_assignments,
        hadir_hari_ini=hadir_hari_ini
    )

# -------------------------------------------------------------
# ⚙️  HALAMAN ABOUT (Opsional)
# -------------------------------------------------------------
@main_bp.route('/about')
def about():
    return render_template('about.html', title='Tentang Sistem HR Portal')