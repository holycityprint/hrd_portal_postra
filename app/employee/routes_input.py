import os, uuid, traceback
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from werkzeug.utils import secure_filename
from app.models import db, Employee, EmployeeDocument, EmployeePersonalDetail
from app.role_check import role_required   # ✅ untuk batasi akses ke HR/Admin

employee_input_bp = Blueprint('employee_input_bp', __name__)

UPLOAD_FOLDER = 'app/static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

# ---------- Fungsi bantu ----------
def allowed_file(filename):
    """Cek ekstensi file"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def to_int(value):
    """Konversi aman string ke int"""
    try:
        return int(value) if value else None
    except (ValueError, TypeError):
        return None


# ===============================================================
# 🟢 Tambah Karyawan Baru — Form Input
# ===============================================================
@employee_input_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def add_employee():
    if request.method == 'POST':
        try:
            nama = request.form.get('nama_lengkap') or "Tanpa Nama"
            posisi = 'Baru'
            jenis_pekerjaan = 'Belum Ditentukan'

            # ---------- Simpan data utama ----------
            new_employee = Employee(name=nama, position=posisi, job_type=jenis_pekerjaan)
            db.session.add(new_employee)
            db.session.flush()  # agar ID langsung tersedia

            # ---------- Konversi tanggal lahir ----------
            tanggal_str = request.form.get('tanggal_lahir')
            tgl_lahir = None
            if tanggal_str:
                try:
                    tgl_lahir = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
                except ValueError:
                    flash("⚠️ Format tanggal salah, diabaikan.", "warning")

            # ---------- Simpan detail pribadi ----------
            detail = EmployeePersonalDetail(
                employee_id=new_employee.id,
                nik=request.form.get('nik'),
                full_name=nama,
                nickname=request.form.get('nama_panggilan'),
                gender=request.form.get('jenis_kelamin'),
                birth_place=request.form.get('tempat_lahir'),
                birth_date=tgl_lahir,  # ✅ sudah objek date
                address_ktp=request.form.get('alamat_ktp'),
                address_current=request.form.get('alamat_sekarang'),
                education=request.form.get('pendidikan'),
                last_job=request.form.get('pekerjaan_terakhir'),
                blood_type=request.form.get('gol_darah'),
                height_cm=to_int(request.form.get('tinggi_badan')),
                weight_kg=to_int(request.form.get('berat_badan')),
                shirt_size=request.form.get('ukuran_kemeja'),
                shoe_size=to_int(request.form.get('ukuran_sepatu')),
                marital_status=request.form.get('status_pernikahan'),
                spouse_name=request.form.get('nama_pasangan'),
                spouse_job=request.form.get('pekerjaan_pasangan'),
                num_children=to_int(request.form.get('jumlah_anak')),
                bpjs_ketenagakerjaan=request.form.get('bpjs_ket'),
                bpjs_kesehatan=request.form.get('bpjs_kes'),
                bpjs_kis=request.form.get('bpjs_kis'),
                jamkesda=request.form.get('jamkesda'),
                emergency_contact_name=request.form.get('emergency_nama'),
                emergency_phone=request.form.get('emergency_hp'),
                emergency_relation=request.form.get('emergency_hubungan'),
                emergency_address=request.form.get('emergency_alamat'),
            )
            db.session.add(detail)

            # ---------- Upload dokumen ----------
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            for key in ('ijazah', 'ktp', 'foto'):
                file = request.files.get(key)
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                    file.save(os.path.join(UPLOAD_FOLDER, filename))

                    doc = EmployeeDocument(
                        employee_id=new_employee.id,
                        document_type=key.upper(),
                        file_path=f"static/uploads/{filename}"
                    )
                    db.session.add(doc)

            db.session.commit()
            flash("✅ Data karyawan berhasil disimpan ke database!", "success")
            return redirect(url_for('employee_input_bp.view_employee', emp_id=new_employee.id))

        except Exception as e:
            db.session.rollback()
            print("❌ ERROR SIMPAN DATA:", e)
            traceback.print_exc()
            flash(f"Terjadi kesalahan saat simpan: {e}", "danger")

    # --- GET: tampilkan form ---
    return render_template('employee/form_input.html')


# ===============================================================
# 👁️ Lihat Detail Karyawan (siap cetak PDF)
# ===============================================================
@employee_input_bp.route('/view/<int:emp_id>')
@login_required
@role_required('admin', 'hr')
def view_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    detail = emp.personal_detail
    docs = emp.documents
    return render_template('employee/view_employee.html',
                           employee=emp, detail=detail, docs=docs)


# ===============================================================
# 📋 Tabel Data Seluruh Karyawan
# ===============================================================
@employee_input_bp.route('/list')
@login_required
@role_required('admin', 'hr')
def list_employees():
    employees = Employee.query.join(EmployeePersonalDetail).all()
    return render_template('employee/list_employees.html', employees=employees)