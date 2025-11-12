import os, uuid
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import Employee, Client, Attendance, Assignment, User, ActivityLog
from app import db
from app.role_check import role_required

# ============================================================
# 🔧 KONFIGURASI BLUEPRINT
# ============================================================
hr_bp = Blueprint('hr', __name__)

UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ============================================================
# ✳️  KELOLA KARYAWAN
# ============================================================
@hr_bp.route('/employees', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def manage_employees():
    clients = Client.query.all()

    if request.method == 'POST':
        name = request.form.get('name')
        position = request.form.get('position')
        job_type = request.form.get('job_type')
        client_id = request.form.get('client_id')
        file = request.files.get('photo')

        # Username otomatis
        username = name.lower().replace(" ", "_")
        default_password = "123456"

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f"⚠️ Username {username} sudah ada, ubah sedikit nama karyawan.", "warning")
            return redirect(url_for('hr.manage_employees'))

        new_user = User(username=username, role='employee', active=True)
        new_user.set_password(default_password)
        db.session.add(new_user)
        db.session.flush()

        filename = 'default_user.png'
        if file and allowed_file(file.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))

        new_employee = Employee(
            name=name,
            position=position,
            job_type=job_type,
            client_id=client_id,
            join_date=date.today(),
            status='aktif',
            photo=filename,
            user_id=new_user.id
        )
        db.session.add(new_employee)
        db.session.flush()

        if client_id:
            new_assignment = Assignment(
                employee_id=new_employee.id,
                client_id=client_id,
                start_date=date.today(),
                status='aktif'
            )
            db.session.add(new_assignment)

        db.session.commit()
        flash(
            f"✅ Data karyawan '{name}' berhasil disimpan dan ditugaskan ke client!<br>"
            f"Akun login dibuat otomatis: <b>{username}</b> / {default_password}",
            "success"
        )
        return redirect(url_for('hr.manage_employees'))

    employees = Employee.query.all()
    return render_template('hr/employee_cards.html', employees=employees, clients=clients)


# ============================================================
# 📊  DASHBOARD HR
# ============================================================
@hr_bp.route('/dashboard')
@login_required
@role_required('admin', 'hr')
def dashboard_hr():
    total_employees = Employee.query.count()
    active_employees = Employee.query.filter_by(status='aktif').count()
    total_clients = Client.query.count()
    total_assignments = Assignment.query.filter_by(status='aktif').count()

    employees = Employee.query.filter_by(status='aktif').all()
    return render_template(
        'hr/dashboard_hr.html',
        total_employees=total_employees,
        active_employees=active_employees,
        total_clients=total_clients,
        total_assignments=total_assignments,
        employees=employees
    )

# ============================================================
# ✏️  EDIT DATA KARYAWAN
# ============================================================
@hr_bp.route('/employees/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    clients = Client.query.all()

    if request.method == 'POST':
        # 🔍 tampilkan isi form saat debug
        print("==== FORM ====", request.form)
        print("==== FILES ====", request.files)

        # ambil data dengan .get() agar tidak BadRequestKeyError
        employee.name       = request.form.get('name')
        employee.position   = request.form.get('position')
        employee.job_type   = request.form.get('job_type')
        employee.status     = request.form.get('status')
        employee.client_id  = request.form.get('client_id')

        # handle foto baru
        file = request.files.get('photo')
        if file and allowed_file(file.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            employee.photo = filename

        db.session.commit()
        flash(f"✅ Data {employee.name} berhasil diperbarui!", "success")
        return redirect(url_for('hr.manage_employees'))

    return render_template('hr/edit_employee.html',
                           employee=employee,
                           clients=clients)


# ============================================================
# 👁️  DETAIL KARYAWAN (Absensi & Aktivitas)
# ============================================================
@hr_bp.route('/employees/<int:id>/details')
@login_required
@role_required('admin', 'hr')
def employee_details(id):
    employee = Employee.query.get_or_404(id)
    attendance_records = Attendance.query.filter_by(employee_id=id).order_by(Attendance.date.desc()).all()
    work_logs = ActivityLog.query.filter_by(employee_id=id).order_by(ActivityLog.created_at.desc()).all()

    return render_template(
        'hr/employee_details.html',
        employee=employee,
        attendance_records=attendance_records,
        work_logs=work_logs
    )


# ============================================================
# 🕒  DASHBOARD ABSENSI UMUM
# ============================================================
@hr_bp.route('/attendance')
@login_required
@role_required('admin', 'hr')
def attendance_dashboard():
    today = date.today()
    employees = Employee.query.join(Client).add_entity(Client).all()
    attendance_today = {
        a.employee_id: a for a in Attendance.query.filter_by(date=today).all()
    }

    total_employee = len(employees)
    hadir = len([a for a in attendance_today.values() if a.status == 'hadir'])
    sakit = len([a for a in attendance_today.values() if a.status == 'sakit'])
    izin = len([a for a in attendance_today.values() if a.status == 'izin'])
    alfa = total_employee - (hadir + sakit + izin)

    return render_template(
        'hr/attendance_dashboard.html',
        today=today,
        total_employee=total_employee,
        hadir=hadir,
        sakit=sakit,
        izin=izin,
        alfa=alfa,
        employees=employees,
        attendance_today=attendance_today
    )


# ============================================================
# 🕓  HALAMAN ABSENSI PERSONAL
# ============================================================
@hr_bp.route('/attendance/<int:employee_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def employee_attendance_page(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    today = date.today()
    attendance = Attendance.query.filter_by(employee_id=employee_id, date=today).first()

    if request.method == 'POST':
        action = request.form.get('action')
        current_time = datetime.now().time()

        if not attendance:
            attendance = Attendance(employee_id=employee_id, date=today, status='hadir')
            db.session.add(attendance)

        if action == 'clock_in' and not attendance.check_in:
            attendance.check_in = current_time
            flash('✅ Absen masuk berhasil!', 'success')
        elif action == 'clock_out' and not attendance.check_out:
            attendance.check_out = current_time
            flash('👋 Absen pulang berhasil!', 'info')

        db.session.commit()
        return redirect(url_for('hr.employee_attendance_page', employee_id=employee_id))

    activity_logs = ActivityLog.query.filter_by(employee_id=employee_id).filter(
        db.func.date(ActivityLog.created_at) == today
    ).all()

    return render_template(
        'hr/employee_attendance_page.html',
        employee=employee,
        attendance=attendance,
        activity_logs=activity_logs
    )


# ============================================================
# 🚚  DASHBOARD OPERASIONAL
# ============================================================
@hr_bp.route('/operation')
@login_required
@role_required('admin', 'hr')
def operation_dashboard():
    """Dashboard operasional: pantau aktivitas & absen harian semua karyawan"""
    today = date.today()

    active_employees = Employee.query.filter(Employee.status == 'aktif').all()
    attendance_today = {
        a.employee_id: a for a in Attendance.query.filter_by(date=today).all()
    }
    activities_today = ActivityLog.query.filter(
        db.func.date(ActivityLog.created_at) == today
    ).order_by(ActivityLog.employee_id).all()

    logs_grouped = {}
    for act in activities_today:
        logs_grouped.setdefault(act.employee_id, []).append(act)

    return render_template(
        'hr/operation_dashboard.html',
        employees=active_employees,
        attendance_today=attendance_today,
        logs_grouped=logs_grouped,
        today=today
    )


# ============================================================
# 🗑️  HAPUS DATA
# ============================================================
@hr_bp.route('/employees/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin', 'hr')
def delete_employee(id):
    emp = Employee.query.get_or_404(id)
    db.session.delete(emp)
    db.session.commit()
    flash(f"🗑️ Data {emp.name} berhasil dihapus.", "info")
    return redirect(url_for('hr.manage_employees'))


# ============================================================
# 👤 DETAIL KARYAWAN OPERASIONAL (riwayat absen + aktivitas + filter tanggal)
# ============================================================
@hr_bp.route('/operation/<int:employee_id>', methods=['GET'])
@login_required
@role_required('admin', 'hr')
def operation_detail(employee_id):
    employee = Employee.query.get_or_404(employee_id)

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        flash("Format tanggal tidak valid.", "warning")
        return redirect(url_for('hr.operation_dashboard'))

    query = Attendance.query.filter_by(employee_id=employee_id).order_by(Attendance.date.desc())
    if start_date and end_date:
        query = query.filter(Attendance.date.between(start_date, end_date))
    elif start_date:
        query = query.filter(Attendance.date >= start_date)
    elif end_date:
        query = query.filter(Attendance.date <= end_date)
    attendance_history = query.all()

    logs_query = ActivityLog.query.filter_by(employee_id=employee_id)
    if start_date and end_date:
        logs_query = logs_query.filter(db.func.date(ActivityLog.created_at).between(start_date, end_date))
    elif start_date:
        logs_query = logs_query.filter(db.func.date(ActivityLog.created_at) >= start_date)
    elif end_date:
        logs_query = logs_query.filter(db.func.date(ActivityLog.created_at) <= end_date)
    work_logs = logs_query.order_by(ActivityLog.created_at.desc()).all()

    return render_template(
        'hr/operation_detail.html',
        employee=employee,
        attendance_history=attendance_history,
        work_logs=work_logs,
        start_date=start_date,
        end_date=end_date
    )

# ============================================================
# 🧾  KELOLA CLIENT (BARU - Dashboard HR)
# ============================================================
@hr_bp.route('/clients', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def manage_clients():
    """HR/Admin dapat menambah client baru dan melihat semua client."""
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        contact_person = request.form.get('contact_person')
        phone = request.form.get('phone')

        username = name.lower().replace(" ", "_")
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("⚠️ Username client sudah ada. Ganti nama perusahaan.", "warning")
            return redirect(url_for('hr.manage_clients'))

        user = User(username=username, role='client', active=True)
        user.set_password('client123')
        db.session.add(user)
        db.session.flush()

        new_client = Client(
            name=name,
            address=address,
            contact_person=contact_person,
            phone=phone,
            user_id=user.id
        )
        db.session.add(new_client)
        db.session.commit()
        flash(f"✅ Client '{name}' berhasil ditambahkan! Akun login: {username} / client123", "success")
        return redirect(url_for('hr.manage_clients'))

    clients = Client.query.order_by(Client.name.asc()).all()
    return render_template('hr/manage_clients.html', clients=clients)


# ============================================================
# 🗑️  HAPUS CLIENT
# ============================================================
@hr_bp.route('/clients/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin', 'hr')
def delete_client(id):
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    flash(f"🗑️ Client {client.name} berhasil dihapus.", "info")
    return redirect(url_for('hr.manage_clients'))
