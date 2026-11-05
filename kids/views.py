from django.template.defaulttags import register
from datetime import date
from .models import Parent, FeeStructure, Attendance, StudentMark
from .forms import StudentForm
from django.contrib import messages
import shutil
from django.conf import settings
from .models import HeadComment
from kids.models import AcademicWeek,  Term
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import StudentTermResult, StudentParent
from django.utils import timezone
import io
import os
from django.http import HttpResponse
from docx.shared import Inches
from .models import StudentActivity, SubjectEnrollment
from pathlib import Path
from docxtpl import DocxTemplate, InlineImage


def get_active_subject_ids_for_student(student):
    """Return list of subject IDs where student is NOT excluded"""
    excluded_subj_ids = SubjectEnrollment.objects.filter(
        student=student, is_active=False
    ).values_list('subject_id', flat=True)
    return excluded_subj_ids

def is_student_active_in_subject(student, subject):
    return not SubjectEnrollment.objects.filter(
        student=student, subject=subject, is_active=False
    ).exists()


if os.path.exists(r"C:\school_management_sys"):
    BASE_KIDS = Path(r"C:\school_management_sys\kids")
else:
    BASE_KIDS = Path(settings.BASE_DIR) / "kids"


def get_student_photo_path(form_or_grade, adm_no):
    # cleans inputs like "Form 3A" -> "Form_3A"
    safe_form = str(form_or_grade).strip().replace(" ", "_")
    #safe_class = str(grade_name).strip().replace(" ", "_")

    folder = BASE_KIDS / "class_photos" / safe_form
    # try png then jpg
    png_path = folder / f"{adm_no}.png"
    jpg_path = folder / f"{adm_no}.jpg"

    if png_path.exists():
        return png_path
    if jpg_path.exists():
        return jpg_path
    # fallback: try directly in Form_3A folder
    return None


def get_stamp_path():
    return BASE_KIDS / "school" / 'Date_Stamp.png'


@register.filter
def dict_get(d, k):
    return d.get(k)


def main_menu(request):
    return render(request, 'kids/main_menu.html')

def school_fees(request):
    if request.method == 'POST':
        if 'add_payment' in request.POST:
            student_id = request.POST['student']
            amount = request.POST['amount']
            term = request.POST['term']
            #Payment.objects.create(student_id=student_id, amount=amount, term=term)

        if 'add_student' in request.POST:

            # 1. Get fee total from FeeStructure based on Grade - FIX 1

            grade = request.POST['grade']

            fee_struct = FeeStructure.objects.filter(grade=grade).first()

            total_fee = fee_struct.total if fee_struct else 300.00  # fallback to 300 if no structure yet

            # 2. Create Student with DOB, Gender, correct fee - FIX 2,3

            student = Student.objects.create(

                first_name=request.POST['first_name'],

                last_name=request.POST['last_name'],

                grade=grade,

                gender=request.POST.get('gender'),

                date_of_birth=request.POST.get('date_of_birth') or None,

                date_joined=request.POST.get('date_of_admission') or None,

                fee_required=total_fee,  # THIS IS THE KEY FIX

            )

            # 3. Helper to create parent and link - FIX 4

            def add_parent(name, phone, address, relationship, is_primary=False):

                if name and phone:  # both required to avoid unique error

                    parent, created = Parent.objects.get_or_create(

                        phone=phone,

                        defaults={'full_name': name, 'relationship': relationship, 'address': address}

                    )

                    StudentParent.objects.get_or_create(

                        student=student,

                        parent=parent,

                        defaults={'is_primary_contact': is_primary}

                    )

            add_parent(request.POST.get('guardian1_name'), request.POST.get('guardian1_phone'),
                       request.POST.get('guardian1_address'), request.POST.get('guardian1_relationship'), True)

            add_parent(request.POST.get('guardian2_name'), request.POST.get('guardian2_phone'),
                       request.POST.get('guardian2_address'), request.POST.get('guardian2_relationship'))

            return redirect('school_fees')

    term_filter = request.GET.get('term', '')  # Get ?term=Term 1 from URL

    students = Student.objects.all()

    context = {
        'students': students,
        'term_filter': term_filter,
    }
    return render(request, 'kids/school_fees.html', context)


def school_register(request):
    grade = request.GET.get('grade', 'FORM 3A')
    year = request.GET.get('year', '2026')
    term = request.GET.get('term', '3')

    # 1. Classes from Student table - dynamic
    all_classes = Student.objects.values_list('grade', flat=True).distinct().order_by('grade')
    if not all_classes:
        all_classes = ['FORM 1A', 'FORM 1B', 'FORM 2A', 'FORM 3A', 'FORM 4A']

    # 2. FIX: Years from start_date year - NOT from 'year' field
    # Your Term model has start_date, end_date, name
    try:
        from .models import Term
        terms_qs = Term.objects.all()
        # Get years from start_date
        all_years = sorted(set([t.start_date.year for t in terms_qs if t.start_date]), reverse=True)
        if not all_years:
            all_years = [2024, 2025, 2026]

        all_terms_objs = terms_qs.order_by('start_date')
        # Build term list like Term 1, Term 2, Term 3 from name
        all_terms = ['1', '2', '3']  # keep simple for now

        # Find current term based on year and term number
        term_obj = None
        for t in terms_qs:
            if str(t.start_date.year) == str(year) and term in t.name:
                term_obj = t
                break
        if not term_obj:
            term_obj = terms_qs.filter(is_current=True).first()
    except Exception as e:
        print(f"Term error: {e}")
        all_years = [2024, 2025, 2026]
        all_terms = ['1', '2', '3']
        term_obj = None

    # Term label
    if term_obj:
        term_label = f"{term_obj.start_date.strftime('%d %b %Y')} to {term_obj.end_date.strftime('%d %b %Y')} ({term_obj.name})"
        term_start = term_obj.start_date
        term_end = term_obj.end_date
    else:
        # Fallback Term 3 2026 - 08 Sep to 05 Dec
        term_start = date(int(year), 9, 8) if term == '3' else date(int(year), 5, 5) if term == '2' else date(int(year),
                                                                                                              1, 10)
        term_end = date(int(year), 12, 5) if term == '3' else date(int(year), 8, 2) if term == '2' else date(int(year),
                                                                                                             4, 5)
        term_label = f"{term_start.strftime('%d %b %Y')} to {term_end.strftime('%d %b %Y')} (64 Days - 14 Weeks Mon-Fri)"

    students_qs = Student.objects.filter(grade=grade).order_by('last_name')
    for s in students_qs:
        s.present_count = Attendance.objects.filter(student=s, date__year=int(year),
                                                    status='Present').count() if year.isdigit() else 0
        s.absent_count = Attendance.objects.filter(student=s, date__year=int(year),
                                                   status='Absent').count() if year.isdigit() else 0
        s.sick_count = Attendance.objects.filter(student=s, date__year=int(year),
                                                 status='Sick').count() if year.isdigit() else 0
        s.total_days = s.present_count + s.absent_count + s.sick_count

    today = date.today()  # or timezone.now().date()

    # LIVE SCHOOL TOTALS - TODAY
    total_enrolment = Student.objects.count()
    today_present = Attendance.objects.filter(date=today, status='Present').count()
    today_absent = Attendance.objects.filter(date=today, status='Absent').count()
    today_sick = Attendance.objects.filter(date=today, status='Sick').count()
    today_possible = today_present + today_absent + today_sick
    attendance_rate = round((today_present / today_possible * 100) if today_possible else 0, 1)

    # Per class live today
    classes_live = []
    for g in all_classes:
        enrol = Student.objects.filter(grade=g).count()
        pres = Attendance.objects.filter(date=today, student__grade=g, status='Present').count()
        classes_live.append({'grade': g, 'enrol': enrol, 'present': pres})


    context = {
        'today': today,
        'total_enrolment': total_enrolment,
        'today_present': today_present,
        'today_absent': today_absent,
        'today_sick': today_sick,
        'today_possible': today_possible,
        'attendance_rate': attendance_rate,
        'classes_live': classes_live,
        'grade': grade,
        'year': year,
        'term': term,
        'all_classes': all_classes,
        'all_years': all_years,
        'all_terms': all_terms,
        'students': students_qs,
        'total_students': students_qs.count(),
        'girls_count': students_qs.filter(gender__icontains='F').count(),
        'boys_count': students_qs.filter(gender__icontains='M').count(),
        'term_label': term_label,
    }
    return render(request, 'kids/school_register.html', context)


def class_register(request, grade):
    today = date.today()
    students = Student.objects.filter(grade=grade).order_by('last_name')

    # Get today's attendance records for this grade
    attendance_today = {a.student_id: a.status for a in Attendance.objects.filter(grade=grade, date=today)}

    if request.method == 'POST':
        # Clear today's records for this grade first, then re-save
        Attendance.objects.filter(grade=grade, date=today).delete()

        for student in students:
            status = request.POST.get(f'status_{student.id}', 'Absent')  # get status from radio buttons
            Attendance.objects.create(student=student, grade=grade, status=status, date=today)

        return redirect('class_register', grade=grade)

    # Stats for header
    present_count = list(attendance_today.values()).count('Present')
    sick_count = list(attendance_today.values()).count('Sick')
    absent_count = list(attendance_today.values()).count('Absent')

    context = {
        'grade': grade,
        'students': students,
        'attendance_today': attendance_today,  # dict {student_id: status}
        'today': today,
        'total': students.count(),
        'present_count': present_count,
        'sick_count': sick_count,
        'absent_count': absent_count,
    }
    return render(request, 'kids/class_register.html', context)

#def class_register(request, grade):
#    today = date.today()
#    students = Student.objects.filter(grade=grade).order_by('last_name')

#    # Get today's attendance records for this grade
#    attendance_today = {a.student_id: a.status for a in Attendance.objects.filter(grade=grade, date=today)}

#    if request.method == 'POST':
#        # Clear today's records for this grade first, then re-save
#        Attendance.objects.filter(grade=grade, date=today).delete()

#        for student in students:
#            status = request.POST.get(f'status_{student.id}', 'Absent')  # get status from radio buttons
#            Attendance.objects.create(student=student, grade=grade, status=status, date=today)

#        return redirect('class_register', grade=grade)

#    # Stats for header
#    present_count = list(attendance_today.values()).count('Present')
#    sick_count = list(attendance_today.values()).count('Sick')
#    absent_count = list(attendance_today.values()).count('Absent')

#    context = {
#        'grade': grade,
#        'students': students,
#        'attendance_today': attendance_today,  # dict {student_id: status}
#        'today': today,
#        'total': students.count(),
#        'present_count': present_count,
#        'sick_count': sick_count,
#        'absent_count': absent_count,
#    }
#    return render(request, 'kids/class_register.html', context)


@login_required
def add_student(request):
    fee_structures = FeeStructure.objects.all().order_by('grade')  # ADD THIS

    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('school_fees')
    else:
        form = StudentForm()

    return render(request, 'kids/add_student.html', {
        'form': form,
        'fee_structures': fee_structures  # ADD THIS
    })

@login_required
def report_cards(request):
    grades = FeeStructure.objects.values_list('grade', flat=True).distinct().order_by('grade')
    return render(request, 'kids/select_grade_report.html', {'grades': grades})

@login_required
def student_summaries_cards(request):
    grades = FeeStructure.objects.values_list('grade', flat=True).distinct().order_by('grade')
    return render(request, 'kids/student_summaries.html', {'grades': grades})

@login_required
def grade_subjects(request, grade):
    subjects = Subject.objects.filter(grade=grade).order_by('name')
    return render(request, 'kids/select_subject.html', {
        'grade': grade,
        'subjects': subjects
    })

@login_required
def marksheet(request, grade, subject_id):
    subject = get_object_or_404(Subject, id=subject_id, grade=grade)
    students = Student.objects.filter(grade=grade).order_by('adm_no')

    term_name = request.GET.get('term', 'Term 3')
    term_obj = Term.objects.filter(name=term_name).first() or Term.objects.first()

    marks = {}
    for s in students:
        m = Mark.objects.filter(student=s, subject=subject, term=term_name).first()
        marks[s.id] = {
            'admission_avg': m.admission_avg if m else '',
            'previous_avg': m.previous_avg if m else '',
            'current_exam_mark': m.current_exam_mark if m else '',
            'current_project_mark': m.current_project_mark if m else '',
            'current_avg': m.current_avg if m else '',
            'current_grade': m.current_grade if m else '',
            'trend': m.trend if m else '0.00',
            'remarks': m.remarks if m else '',
            'trs_initials': m.trs_initials if m else '',
        }

    if request.method == 'POST':
        term = request.POST.get('term', term_name)
        trend_base = request.POST.get('trend_base', 'admission')  # <-- from button
        first_initial = None

        if request.method == 'POST':
            term = request.POST.get('term', term_name)
            trend_base = request.POST.get('trend_base', 'admission')

            # === CLEAR BATTLEFIELD ===
            if 'clear_marks' in request.POST:
                for student in students:
                    m = Mark.objects.filter(student=student, subject=subject, term=term).first()
                    if m:
                        m.current_exam_mark = None
                        m.current_project_mark = None
                        m.current_avg = None
                        m.current_grade = None
                        m.trend = Decimal('0.00')
                        m.trs_initials = ''
                        m.remarks = ''
                        m.save()
                return redirect(f"{request.path}?term={term}&trend_base={trend_base}")

            first_initial = None

        for i, student in enumerate(students):
            adm = request.POST.get(f'admission_avg_{student.id}')
            exam = request.POST.get(f'current_exam_{student.id}')
            project = request.POST.get(f'current_project_{student.id}')
            #initials = request.POST.get(f'trs_initials_{student.id}')

           # AUTO FILL INITIALS: copy first one down
            initials = request.POST.get(f'trs_initials_{student.id}', '')

            if initials and initials.strip() == 'None':
                initials = ''

            if i == 0 and initials:
                first_initial = initials.strip().upper()

            if first_initial and i != 0:
                initials = first_initial

            adm_val = Decimal(adm) if adm not in [None, ''] else None
            exam_val = Decimal(exam) if exam not in [None, ''] else None
            proj_val = Decimal(project) if project not in [None, ''] else None

            mark_obj, created = Mark.objects.get_or_create(student=student, subject=subject, term=term)

            # CURRENT AVG
            current_avg = None
            current_grade = None
            if exam_val is not None or proj_val is not None:
                current_avg = ((exam_val or Decimal(0)) + (proj_val or Decimal(0))) / 2
                if current_avg >= 80:
                    current_grade = 'A'
                elif current_avg >= 60:
                    current_grade = 'B'
                elif current_avg >= 50:
                    current_grade = 'C'
                elif current_avg >= 40:
                    current_grade = 'D'
                elif current_avg >= 30:
                    current_grade = 'E'
                else:
                    current_grade = 'U'

            # === TREND - KEEP OLD ADMISSION IF BLANK ===
            trend_val = Decimal('0.00')
            base = None

            # if input blank, use what is already in DB for this student
            if adm_val is None:
                adm_val = mark_obj.admission_avg

            prev_mark = Mark.objects.filter(student=student, subject=subject).exclude(term=term).exclude(
                current_avg__isnull=True).order_by('-id').first()
            real_prev = prev_mark.current_avg if prev_mark else None

            if trend_base == 'previous':
                base = real_prev if real_prev is not None else mark_obj.previous_avg
                mark_obj.previous_avg = base
            else:  # admission
                base = adm_val

            # FINAL CALC
            if current_avg is not None and base is not None:
                trend_val = current_avg - base
                print(f"DEBUG T001: current={current_avg} base={base} trend={trend_val} base_type={trend_base}")
            else:
                print(f"DEBUG T001 FAILED: current={current_avg} base={base} adm_in_db={mark_obj.admission_avg}")

            mark_obj.admission_avg = adm_val
            mark_obj.current_exam_mark = exam_val
            mark_obj.current_project_mark = proj_val
            mark_obj.current_avg = current_avg
            mark_obj.current_grade = current_grade
            mark_obj.trend = trend_val
            mark_obj.trs_initials = initials
            mark_obj.term = term
            mark_obj.save()

        return redirect(f"{request.path}?term={term}")

    all_terms = Term.objects.all().order_by('name')
    all_terms_for_lock = Term.objects.all().order_by('start_date') # if you have start_date, else use name

    return render(request, 'kids/marksheet.html', {
        'grade': grade,
        'subject': subject,
        'students': students,
        'marks': marks,
        'term': term_name,
        'term_obj': term_obj,
        'selected_term': term_name,  # for locking JS
        'all_terms': all_terms,

    })


def generate_professional_reports(request, grade, grade_letter=None):
    # 1. Setup Paths
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    final_folder = os.path.join(desktop, f"Final_Reports_{grade}")
    temp_folder = os.path.join(settings.BASE_DIR, "temp_reports")
    save_path = os.path.join(os.path.expanduser("~"), "Desktop", f"Reports_{grade}")

    if not os.path.exists(temp_folder): os.makedirs(temp_folder)
    if not os.path.exists(final_folder): os.makedirs(final_folder)

    # 2. Get Data & Calculate Rankings
    students = Student.objects.filter(grade=grade)
    subjects = Subject.objects.filter(grade=grade)

    # Calculate totals first to determine "Position"
    student_results = []
    for student in students:
        marks = Mark.objects.filter(student=student, term='Term 1')
        #total = sum(m.score for m in marks)
        #student_results.append({'id': student.id, 'total': total})
        student_results.append({'id': student.id})

    # 3. Process the Template (The "shutil" way)
    # Make sure you have a file named 'report_template.docx' in your project root
    template_path = os.path.join(settings.BASE_DIR, 'report_card_template.docx')
    template = DocxTemplate(template_path)

    for student in students:
        student_marks = []
        total = 0
        for s in subjects:
            m = Mark.objects.filter(student=student, subject=s).first()
            score = 1 if m else 0
            #score = m.score if m else 0

            total += score

            # Simple Logic for Grade/Comment

            grade_letter = "A" if score >= 75 else "B" if score >= 60 else "C"
            comment = "Excellent" if score >= 75 else "Good effort" if score >= 60 else "Work harder"

            student_marks.append({
                'name': s.name, 'mark': score, 'grade': grade_letter, 'comment': comment
            })

        result = StudentTermResult.objects.filter(student=student, term='Term 1', year=2024).first()
        comment = result.head_teacher_comment if result and result.head_teacher_comment else "No comment recorded"

        context = {'head_teacher_comment': comment,
                   }

        # Context to inject into your Word template
        context = {
            'term': 'Term 1',
            'year': '2024',
            'student_name': f"{student.first_name} {student.last_name}",
            'adm_no': student.adm_no,
            'grade': grade,
            'subjects': student_marks,
            'total_marks': total,
            'average': round(total / len(subjects), 1) if subjects else 0,
            'position': total,
            #'position': rankings.get(student.id),
            'head_comment': student.head_comment or "No comment recorded"  # use this
        }

        template.render(context)
        file_name = f"{student.adm_no}.docx"
        template.save(os.path.join(temp_folder, file_name))

    # 4. Use SHUTIL to move/zip files
    # Move files from temp to Desktop
    for file in os.listdir(temp_folder):
        shutil.move(os.path.join(temp_folder, file), os.path.join(final_folder, file))

    # Optional: Delete the empty temp folder
    shutil.rmtree(temp_folder)

    return redirect('master_marksheet', grade=grade)


@login_required
def head_comments(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    term_obj = Term.objects.filter(is_current=True).first()
    current_term = term_obj.name if term_obj else "Term 1"
    current_year = term_obj.start_date.year if term_obj and term_obj.start_date else timezone.now().year
    grade = student.grade

    # 1. GET MARKS THE RIGHT WAY - no student.marks
    marks_qs = Mark.objects.filter(student=student, term=current_term)

    # 2. CALCULATE AVERAGE AND BUILD SUBJECT LIST
    subjects_data = []
    total = 0
    count = 0

    for m in marks_qs:
        score = m.current_avg if m.current_avg is not None else 0 # CHANGED: was m.score
        total += float(score)
        count += 1
        subjects_data.append({
            'subject': m.subject.name,
            'score': score,
            'low': float(score) < 50  # flag for red highlight
        })

    average = round(total / count, 1) if count > 0 else 0

    # 3. GET OR CREATE THE TERM RESULT RECORD - this is where Head Comment should live
    result, created = StudentTermResult.objects.get_or_create(
        student=student,
        term=current_term,
        year=current_year,
        defaults={'grade': grade}
    )

    # 25 comment templates
    comments = [
        f"Excellent performance {student.first_name}. Keep up the good work.",
        f"Good effort shown. {student.first_name} can improve with more practice.",
        f"Fair performance. {student.first_name} needs more focus and consistency.",
        f"Below expectations. {student.first_name} requires close supervision.",
        f"{student.first_name} is a hardworking student. Well done.",
        f"{student.first_name} shows potential but needs to be more consistent.",
        f"Very good progress this term, {student.first_name}.",
        f"{student.first_name} participates well in class activities.",
        f"Needs to improve time management, {student.first_name}.",
        f"{student.first_name} is respectful and disciplined.",
        f"Good grasp of concepts. Keep pushing, {student.first_name}.",
        f"{student.first_name} should complete assignments on time.",
        f"Encouraging effort from {student.first_name} this term.",
        f"{student.first_name} needs to participate more in class.",
        f"Excellent attitude towards learning, {student.first_name}.",
        f"{student.first_name} requires closer academic monitoring.",
        f"Well behaved and focused, {student.first_name}.",
        f"{student.first_name} shows improvement in most subjects.",
        f"Needs to read more to improve vocabulary, {student.first_name}.",
        f"{student.first_name} is a team player.",
        f"Good problem-solving skills shown by {student.first_name}.",
        f"{student.first_name} should aim higher.",
        f"Satisfactory performance. More effort needed, {student.first_name}.",
        f"{student.first_name} is on the right track.",
        f"Keep working hard, {student.first_name}. Results will follow."
    ]

    if request.method == 'POST':
        comment = request.POST.get('comment')
        result.head_teacher_comment = comment # CHANGED: save to StudentTermResult
        result.save()

        if request.POST.get('action') == 'next':
            next_student = Student.objects.filter(
                grade=student.grade,
                id__gt=student.id
            ).order_by('id').first()
            if next_student:
                return redirect('head_comments', student_id=next_student.id)
        return redirect('class_register', grade=student.grade)

    context = {
        'student': student,
        'grade': grade,
        'term': current_term,
        'average': average,
        'subjects_data': subjects_data,
        'comments': comments,
        'existing_comment': result.head_teacher_comment or '' # CHANGED: read from result
    }

    return render(request, 'kids/head_comments.html', context)


@login_required
def class_teacher_comments(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    term_obj = Term.objects.filter(is_current=True).first()
    current_term = term_obj.name if term_obj else "Term 1"
    current_year = term_obj.start_date.year if term_obj and term_obj.start_date else timezone.now().year
    grade = student.grade

    # GET OR CREATE THE TERM RESULT RECORD
    result, created = StudentTermResult.objects.get_or_create(
        student=student,
        term=current_term,
        year=current_year,
        defaults={'grade': grade}
    )

    # 25 CLASS TEACHER comment templates - Behaviour & Attendance
    comments = [
        f"Excellent conduct and attendance, {student.first_name}. Keep it up.",
        f"Good behaviour shown. {student.first_name} is a pleasure to teach.",
        f"Fair conduct. {student.first_name} needs to be more disciplined in class.",
        f"Poor attendance and behaviour. {student.first_name} requires close monitoring.",
        f"{student.first_name} is well behaved and respectful to everyone.",
        f"{student.first_name} needs to improve punctuality and class participation.",
        f"Very good attitude towards school work, {student.first_name}.",
        f"{student.first_name} relates well with peers and teachers.",
        f"Needs to improve self control, {student.first_name}.",
        f"{student.first_name} is neat, polite and obedient.",
        f"Good leadership qualities shown by {student.first_name}.",
        f"{student.first_name} should avoid noise and distractions in class.",
        f"Encouraging discipline from {student.first_name} this term.",
        f"{student.first_name} needs to be more responsible.",
        f"Excellent role model, {student.first_name}.",
        f"{student.first_name} requires closer supervision on behaviour.",
        f"Well mannered and cooperative, {student.first_name}.",
        f"{student.first_name} shows improvement in conduct.",
        f"Needs to respect school rules more, {student.first_name}.",
        f"{student.first_name} is a team player and helpful.",
        f"Good social skills shown by {student.first_name}.",
        f"{student.first_name} should aim to be more consistent.",
        f"Satisfactory conduct. More effort needed, {student.first_name}.",
        f"{student.first_name} is on the right track behaviour-wise.",
        f"Keep up the good discipline, {student.first_name}. Well done."
    ]

    if request.method == 'POST':
        comment = request.POST.get('comment')
        result.teacher_comment = comment # SAVING TO TEACHER COMMENT FIELD
        result.save()

        if request.POST.get('action') == 'next':
            next_student = Student.objects.filter(
                grade=student.grade,
                id__gt=student.id
            ).order_by('id').first()
            if next_student:
                return redirect('class_teacher_comments', student_id=next_student.id)
        return redirect('class_register', grade=student.grade)

    context = {
        'student': student,
        'grade': grade,
        'term': current_term,
        'comments': comments,
        'existing_comment': result.teacher_comment or ''
    }

    return render(request, 'kids/class_teacher_comments.html', context)


REMARK_MAP = {
    # NEGATIVE TRENDS - 10 sets
    'N10': (-100, -51, [
        "Severe drop in performance. Urgent intervention required.",
        "Significant decline. Needs immediate remedial work.",
        "Drastic fall in standard. Requires close supervision."
    ]),
    'N9': (-50, -41, [
        "Sharp decline observed. Needs to redouble efforts.",
        "Marked drop. Must revisit fundamentals.",
        "Considerable decrease. Extra work needed."
    ]),
    'N8': (-40, -31, [
        "Worrying downward trend. Needs to work harder.",
        "Performance has slipped notably. Requires attention.",
        "Consistent effort lacking. Must improve."
    ]),
    'N7': (-30, -26, [
        "Performance below expected level. Needs to pull up.",
        "Drop in attainment. More revision required.",
        "Below previous standard. Needs guidance."
    ]),
    'N6': (-25, -21, [
        "Slight but clear decline. Needs to focus more.",
        "Performance has dipped. Must be more consistent.",
        "Needs to avoid complacency."
    ]),
    'N5': (-20, -16, [
        "Some decline noted. Requires more practice.",
        "Performance has fallen slightly. Can do better.",
        "Needs to improve concentration."
    ]),
    'N4': (-15, -11, [
        "Minor drop. Needs to maintain previous effort.",
        "Slight decline. Requires steady revision.",
        "Needs to be more attentive in class."
    ]),
    'N3': (-10, -6, [
        "Almost maintaining standard. Needs little more push.",
        "Marginal decline. Can recover easily.",
        "Needs to sustain effort."
    ]),
    'N2': (-5, -3, [
        "Slightly below previous. Needs consistency.",
        "Performance fairly stable. Slight improvement needed.",
        "Needs to keep up momentum."
    ]),
    'N1': (-2, -1, [
        "Performance steady with slight fluctuation.",
        "Maintaining average. Needs to aim higher.",
        "Fair performance. More effort required."
    ]),

    # NEUTRAL
    'Z0': (0, 0, [
        "Performance maintained at same level.",
        "Steady progress observed. Keep it up.",
        "Consistent performance."
    ]),

    # POSITIVE TRENDS - 10 sets
    'P1': (1, 2, [
        "Slight improvement noted. Keep it up.",
        "Marginal gain observed. More effort needed.",
        "Moving in right direction."
    ]),
    'P2': (3, 5, [
        "Fair improvement shown. Can do better.",
        "Encouraging progress. Maintain effort.",
        "Shows signs of improvement."
    ]),
    'P3': (6, 10, [
        "Good improvement. Maintain the momentum.",
        "Positive progress noted. Keep working hard.",
        "Improved performance. Well done."
    ]),
    'P4': (11, 15, [
        "Commendable improvement. Keep it up.",
        "Good progress. Shows commitment.",
        "Noticeable improvement. Well done."
    ]),
    'P5': (16, 20, [
        "Very good improvement. Keep up the hard work.",
        "Impressive progress. Continue like this.",
        "Strong improvement shown."
    ]),
    'P6': (21, 25, [
        "Excellent improvement. Highly commendable.",
        "Remarkable progress. Keep it up.",
        "Great improvement in performance."
    ]),
    'P7': (26, 30, [
        "Outstanding improvement. Keep the spirit.",
        "Excellent work. Shows great potential.",
        "Tremendous progress. Well done."
    ]),
    'P8': (31, 40, [
        "Exceptional improvement. Very impressive.",
        "Huge leap in performance. Highly commendable.",
        "Fantastic progress. Keep it up."
    ]),
    'P9': (41, 50, [
        "Extraordinary improvement. Top effort.",
        "Excellent turnaround. Keep soaring.",
        "Brilliant improvement. Well done."
    ]),
    'P10': (51, 100, [
        "Phenomenal improvement. Keep excelling.",
        "Outstanding turnaround. Excellent work.",
        "Superb progress. Highly impressive."
    ]),
}

def get_remark_data(trend):
    if trend is None:
        return None, []
    try:
        t = float(trend)
    except:
        return None, []
    if t > 100 or t < -100:
        return "ERROR", ["Error in Input Marks"]
    for group, (low, high, options) in REMARK_MAP.items():
        if low <= t <= high:
            return group, options
    return None, []

def enter_marks(request, term_id, subject_id):
    students = Student.objects.filter(is_active=True)
    term = Term.objects.get(id=term_id)
    subject = Subject.objects.get(id=subject_id)

    marks = {}
    for s in students:
        mark, _ = StudentMark.objects.get_or_create(student=s, term=term, subject=subject)
        group, options = get_remark_data(mark.trend)
        marks[s.id] = {
            'obj': mark,
            'trend': mark.trend,
            'remarks': mark.remarks,
            'needs_popup': len(options) > 1 and not mark.remarks,
            'options': options,
        }

    if request.method == 'POST':
        for s in students:
            mark = marks[s.id]['obj']

            # Get marks from form
            curr = request.POST.get(f'current_{s.id}')
            prev = request.POST.get(f'previous_{s.id}')
            adm = request.POST.get(f'admission_{s.id}')

            if curr: mark.current_avg = float(curr)
            if prev: mark.previous_avg = float(prev)
            if adm: mark.admission_avg = float(adm)

            # Calculate trend
            if mark.current_avg is not None:
                base = mark.previous_avg if mark.previous_avg is not None else mark.admission_avg
                if base is not None:
                    mark.trend = mark.current_avg - base

            # Handle remark
            picked_remark = request.POST.get(f'remark_{s.id}')
            group, options = get_remark_data(mark.trend)

            if len(options) == 1: # R or Z
                mark.remarks = options[0]
                mark.remark_locked = True
            elif picked_remark: # Teacher picked from popup
                mark.remarks = picked_remark

            mark.save()

        messages.success(request, "Marks and Remarks Saved")
        return redirect('enter_marks', term_id, subject_id)

    context = {'students': students, 'marks': marks, 'term': term, 'subject': subject}
    return render(request, 'marks/enter_marks.html', context)


from decimal import Decimal

@login_required
def subject_teacher_comments(request, student_id, term_id, subject_id):
    student = get_object_or_404(Student, id=student_id)
    term_obj = get_object_or_404(Term, id=term_id)
    subject = get_object_or_404(Subject, id=subject_id)

    term_name = term_obj.name.strip()  # "Term 1" / "Term 2" / "Term 3"

    # FIX: Search BOTH ways - string and FK - to find any existing mark
    mark = Mark.objects.filter(student=student, subject=subject, term=term_name).first()
    if not mark:
        # try if term is stored as object or id
        mark = Mark.objects.filter(student=student, subject=subject, term__icontains=term_name).first()
    if not mark:
        mark = Mark.objects.filter(student=student, subject=subject, term=str(term_obj.id)).first()

    # If still none -> create it
    if not mark:
        mark = Mark.objects.create(
            student=student,
            subject=subject,
            term=term_name,
            trend=Decimal('0.00'),
            current_avg=Decimal('0.00')
        )

    if request.method == 'POST':
        selected_comment = request.POST.get('comment')
        #initials = request.POST.get('trs_initials')

        if selected_comment:
            mark.remarks = selected_comment
            # also save to comment field if you have it
            if hasattr(mark, 'comment'):
                mark.comment = selected_comment
        #if initials:
         #   mark.trs_initials = initials
        mark.save()

        # Find next student in same class
        #all_students = Student.objects.filter(form=student.form).order_by('adm_no')
        if hasattr(student, 'form') and getattr(student, 'form'):
            all_students = Student.objects.filter(form=student.form).order_by('adm_no')
        elif hasattr(student, 'current_class') and getattr(student, 'current_class'):
            all_students = Student.objects.filter(current_class=student.current_class).order_by('adm_no')
        elif hasattr(student, 'class_assigned') and getattr(student, 'class_assigned'):
            all_students = Student.objects.filter(class_assigned=student.class_assigned).order_by('adm_no')
        elif hasattr(student, 'grade') and getattr(student, 'grade'):
            all_students = Student.objects.filter(grade=student.grade).order_by('adm_no')
        else:
            # Final fallback - same Form 3A from subject.grade
            # marksheet uses /marksheet/Form 3A/50/ -> Form 3A
            grade_name = getattr(subject, 'grade', 'Form 3A')
            all_students = Student.objects.filter(marks__subject=subject).distinct().order_by('adm_no')
            if not all_students.exists():
                all_students = Student.objects.all().order_by('adm_no')

        all_ids = list(all_students.values_list('id', flat=True))
        try:
            curr_idx = all_ids.index(student.id)
            next_id = all_ids[curr_idx + 1] if curr_idx + 1 < len(all_ids) else None
        except:
            next_id = None

        # If you clicked Save & Next and there is next student
        if request.POST.get('action') == 'next' and next_id:
            return redirect(f"/subject-comments/{next_id}/{term_obj.id}/{subject.id}/")

        # Default: Save & Back to marksheet
        return redirect(f"/marksheet/{subject.grade}/{subject.id}/?term={term_name}")

    # FIX: If trend is None -> recalc from DB now
    if mark.trend is None:
        base = mark.admission_avg
        # if base empty, try previous term's avg
        if base is None:
            prev = Mark.objects.filter(student=student, subject=subject).exclude(term=term_name).exclude(
                current_avg__isnull=True).order_by('-id').first()
            if prev:
                base = prev.current_avg
                mark.previous_avg = base

        curr = mark.current_avg
        if curr is not None and base is not None:
            mark.trend = curr - base
        else:
            mark.trend = Decimal('0.00')
        mark.save()

    trend_val = mark.trend or Decimal('0.00')

    # DEBUG for you
    print(f"COMMENT FIXED: {student.adm_no} term={term_name} mark_id={mark.id} trend={trend_val}")

    # === YOUR EXISTING GROUP LOGIC STARTS HERE ===
    # use trend_val not mark.trend
    if trend_val > 0:
        group = f"P{int(trend_val)}" if trend_val <= 10 else "P10+"
    elif trend_val < 0:
        group = f"N{abs(int(trend_val))}" if abs(trend_val) <= 10 else "N10+"
    else:
        group = "Z0"

    # then your options = ... based on group
    # === COMMENT OPTIONS - RESTORE ALL GROUPS ===
    COMMENT_MAP = {
        # Zero / Maintained
        "Z0": [
            "Performance maintained at same level.",
            "Steady progress observed. Keep it up.",
            "Consistent performance.",
            "Hausi kuchinja"
        ],
        # Negative - Drop
        "N1": ["Slight drop noted. Needs more focus.", "Performance slipped slightly.",
               "Can do better with extra effort."],
        "N2": ["Performance declined. Requires attention.", "Drop in performance observed.", "Needs to work harder."],
        "N3": ["Significant drop. Intervention needed.", "Performance deteriorated.", "Must improve considerably."],
        "N10+": ["Major decline. Urgent attention required.", "Performance has dropped drastically.",
                 "Needs serious remedial work."],
        # Positive - Improvement
        "P1": ["Slight improvement noted. Keep it up.", "Showing some progress.", "Encouraging improvement."],
        "P2": ["Good improvement observed.", "Performance improving steadily.", "Keep up the good work."],
        "P3": ["Excellent improvement!", "Remarkable progress made.", "Great improvement shown."],
        "P10+": ["Outstanding improvement! Well done.", "Exceptional progress!", "Tremendous improvement observed."],
    }

    # Normalize group to map keys
    if trend_val == 0:
        group = "Z0"
    elif trend_val < 0:
        abs_t = abs(int(trend_val))
        if abs_t == 1:
            group = "N1"
        elif abs_t == 2:
            group = "N2"
        elif abs_t >= 3 and abs_t <= 5:
            group = "N3"
        else:
            group = "N10+"
    else:  # >0
        abs_t = int(trend_val)
        if abs_t == 1:
            group = "P1"
        elif abs_t == 2:
            group = "P2"
        elif abs_t >= 3 and abs_t <= 5:
            group = "P3"
        else:
            group = "P10+"

    options = COMMENT_MAP.get(group, COMMENT_MAP["Z0"])

    return render(request, 'kids/subject_teacher_comments.html', {
        'student': student,
        'term_obj': term_obj,
        'subject': subject,
        'mark': mark,
        'trend': trend_val,
        'group': group,
        'options': options,
    })


def parent_dashboard(request):
    if request.method == "POST":
        phone = request.POST.get('phone')
        students = Student.objects.filter(parent_phone=phone)

        for child in students:
            excluded_ids = list(SubjectEnrollment.objects.filter(
                student=child, is_active=False
            ).values_list('subject_id', flat=True))

            # Attach to child object so template can use it!
            # 1. Filter MARKS
            child.filtered_marks = Mark.objects.filter(
                student=child
            ).exclude(subject_id__in=excluded_ids)

            # 2. Filter COURSEWORK
            child.filtered_coursework = CourseWorkScore.objects.filter(
                student=child
            ).exclude(marksheet__subject_id__in=excluded_ids)

            # 3. Filter SUBJECTS for buttons - use child's grade
            # If Subject has grade/form field:
            child.filtered_subjects = Subject.objects.filter(
                grade=child.grade
            ).exclude(id__in=excluded_ids) if hasattr(Subject, 'grade') else Subject.objects.exclude(
                id__in=excluded_ids)

        return render(request, 'kids/parent_dashboard.html', {'students': students})

       # return render(request, 'kids/parent_dashboard.html', {'students': students})
    return render(request, 'kids/parent_login.html')


from django.shortcuts import render
from .models import Subject, Student, Mark  # make sure these 3 are imported
from django.db.models import Prefetch


@login_required
def master_marksheet(request, grade):
    term = Term.objects.filter(is_current=True).first()
    term_name = term.name if term else 'Term 1'
    term_year = term.start_date.year if term and term.start_date else date.today().year

    year = date.today().year
    term_start = term.start_date if term and term.start_date else date(year, 1, 1)
    term_end = term.end_date if term and term.end_date else date.today()
    next_term_start = term.end_date if term and term.end_date else date.today()


    students = Student.objects.filter(grade=grade).order_by('last_name')
    subjects = Subject.objects.filter(grade=grade).order_by('order')
    total_students = students.count()
    subject_count = subjects.count() if subjects.count() > 0 else 1

    marks_data = {}
    student_results = {}
    parent_data = {}
    temp_rank_list = [] # NEW: for ranking

    for student in students:
        sid = student.id

        # 1. MARKS DICT
        marks_data[sid] = {}
        for mark in Mark.objects.filter(student=student, term=term_name):
            marks_data[sid][mark.subject_id] = mark

        # 2. TERM RESULT FROM DB
        result = StudentTermResult.objects.filter(student=student, term=term_name, year=term_year).first()

        # Sum all current_avg for this student
        subject_scores = []
        for subject in subjects:
            mark = marks_data[sid].get(subject.id)
            if mark:
                subject_scores.append(mark.current_avg)

        #calc_total = sum(subject_scores)
        calc_total = sum([s or 0 for s in subject_scores])
        calc_avg = calc_total / subject_count if subject_count > 0 else 0

        # Use DB if it has data, otherwise use calculated
        db_total = result.total_marks if result and result.total_marks else 0
        total = db_total if db_total > 0 else calc_total
        avg = float(total) / subject_count if subject_count > 0 else 0

        # 3. ATTENDANCE - BLUE WIRE
        #possible_dates = Attendance.objects.filter(student=student, date__gte=term_start, date__lte=term_end).values('date').distinct().count()
        possible_dates = Attendance.objects.filter(student=student, date__gte=term_start, date__lte=term_end, status__in=['Present', 'Absent', 'Sick', ]).count()
        present_days = Attendance.objects.filter(student=student, date__gte=term_start, date__lte=term_end, status__in=['Present']).count()

        # 4. PINK WIRE 1: SUBJECTS PASSED
        subjects_passed_count = 0
        for subject in subjects:
            mark = marks_data[sid].get(subject.id)
            if mark and mark.current_grade in ['A', 'B', 'C']: # PASS = A, B, C
                subjects_passed_count += 1


        student_results[sid] = {
            'obj': result,
            'total_marks': total,
            'avg': f"{avg:.1f}",
            'position': '-', # placeholder
            'head_teacher_comment': result.head_teacher_comment if result and result.head_teacher_comment else '-',
            'teacher_comment': result.teacher_comment if result and result.teacher_comment else '-',
            'subjects_passed': subjects_passed_count, # PINK WIRE 1 DONE
            'actual_attendance': present_days,
            'possible_attendance': possible_dates,
        }
        temp_rank_list.append({'sid': sid, 'avg': avg}) # collect for ranking

        # 5. PARENT DATA
        sp = StudentParent.objects.filter(student=student, is_primary_contact=True).first()
        if not sp: sp = StudentParent.objects.filter(student=student).first()
        parent = sp.parent if sp else None
        parent_data[sid] = {'name': parent.full_name if parent else '-', 'address': parent.address if parent else '-'}

    # 6. PINK WIRE 2: CLASS POSITION - RANKING
    temp_rank_list.sort(key=lambda x: x['avg'], reverse=True)  # highest avg first
    rank = 0
    for i, item in enumerate(temp_rank_list):
        if i == 0 or item['avg'] != temp_rank_list[i - 1]['avg']:
            rank = i + 1
        student_results[item['sid']]['position'] = rank


    context = {
        'grade': grade, 'term': term, 'students': students, 'subjects': subjects,
        'marks_data': marks_data, 'student_results': student_results, 'parent_data': parent_data,
        'total_students': total_students, 'next_term_start': next_term_start,
        'date': date.today(),
    }
    return render(request, 'kids/master_marksheet.html', context)

def download_report_card(request, student_id, term):
    student = get_object_or_404(Student, pk=student_id)

    marks = Mark.objects.filter(student=student, term=term).select_related('subject').order_by('subject__name')
    term = Term.objects.filter(is_current=True).first()
    term_name = term.name if term else 'Term 3'
    #term_name = term_obj.name if term_obj else term

    #/term_year = term.start_date.year if term and term.start_date else date.today().year
    term_obj = Term.objects.filter(name=term).first() or Term.objects.filter(is_current=True).first()
    term_year = term_obj.start_date.year if term_obj and term_obj.start_date else date.today().year
    marks_qs = Mark.objects.filter(student=student, term=term_name).select_related('subject').order_by('subject__order')
    m_list = list(marks_qs)

    #result = StudentTermResult.objects.filter(student=student, term=term_name, year=term_year).first()
    result = StudentTermResult.objects.filter(student=student, term=term).first()
    parent_qs = StudentParent.objects.filter(student=student).first()
    parent = parent_qs.parent if parent_qs else None

    fee = FeeStructure.objects.filter(grade=student.grade).first()

    grade = student.grade
    subjects = Subject.objects.filter(grade=grade).order_by('order')
    students_in_grade = Student.objects.filter(grade=grade)
    subject_count = subjects.count() or 1


    act_obj = StudentActivity.objects.filter(student=student).first()
    sports_list = [
        'soccer', 'netball', 'basketball', 'rugby', 'tennis', 'hockey', 'athletics',
        'high_jump', 'triple_jump', 'javelin', 'shot_put', 'hop_step_jump', 'swimming'
    ]
    sport_labels = {
        'soccer': 'Soccer', 'netball': 'Netball', 'basketball': 'Basketball', 'rugby': 'Rugby',
        'tennis': 'Tennis', 'hockey': 'Hockey', 'athletics': 'Athletics',
        'high_jump': 'HighJ', 'triple_jump': 'TripJ', 'javelin': 'Javelin',
        'shot_put': 'ShotPut', 'hop_step_jump': 'HSJ', 'swimming': 'Swim'
    }


    # Tray - same order as your card: 4005 English, 4007 Shona, etc
    # We make it safe - if Shona is row 2, it stays row 2
    m_list = list(marks) # 0=English, 1=Shona...

    rank_list = []
    for s in students_in_grade:
        marks_qs = Mark.objects.filter(student=s, term=term)
        total = sum([m.current_avg or 0 for m in marks_qs])
        avg = total / subject_count if subject_count else 0
        rank_list.append({'sid': s.id, 'avg': avg, 'total': total})

    rank_list.sort(key=lambda x: x['avg'], reverse=True)
    # build position map
    position_map = {}
    total_map = {}
    avg_map = {}
    rank = 0
    for i, item in enumerate(rank_list):
        if i == 0 or item['avg'] != rank_list[i - 1]['avg']:
            rank = i + 1
        position_map[item['sid']] = rank
        total_map[item['sid']] = item['total']
        avg_map[item['sid']] = item['avg']

    # Now this student's correct values
    correct_position = position_map.get(student.id, '-')
    correct_total = total_map.get(student.id, 0)
    correct_avg = avg_map.get(student.id, 0)
    total_students = students_in_grade.count()

    # Marks ordered by subject order, not name — to match card tray 1-16
    marks = Mark.objects.filter(student=student, term=term).select_related('subject').order_by('subject__order')
    m_list = list(marks)

    def get_mark(index, field_name):
        if index < len(m_list):
            return getattr(m_list[index], field_name, '') or ''
        return ''

    # attendance same as master
    term_start = term_obj.start_date if term_obj else date.today()
    term_end = term_obj.end_date if term_obj else date.today()
    possible_dates = Attendance.objects.filter(student=student, date__gte=term_start, date__lte=term_end).values(
        'date').distinct().count()
    present_days = Attendance.objects.filter(student=student, date__gte=term_start, date__lte=term_end,
                                             status__in=['Present', 'Sick']).count()
    subjects_passed = sum(1 for m in m_list if getattr(m, 'current_grade', '') in ['A', 'B', 'C'])

    template_path = 'C:/school_management_sys/kids/templates/word/Report_card_template.docx'
    doc = DocxTemplate(template_path)


    position = ''
    total_students = ''
    if result:
        # same class, same term, same year
        class_results = StudentTermResult.objects.filter(
            grade=student.grade, term=term, year=result.year
        ).order_by('-total_marks')

        total_students = str(class_results.count())

        # find position
        for idx, r in enumerate(class_results, start=1):
            if r.student_id == student.pk:
                position = str(idx)
                # save it so next time you don't need to calculate
                if result.position != idx:
                    result.position = idx
                    result.save(update_fields=['position'])
                break

    sports_text = ""
    if act_obj:
        ticked = [sport_labels.get(s, s) for s in sports_list if getattr(act_obj, s, False)]
        clubs = act_obj.clubs or ""
        if ticked:
            sports_text = ", ".join(ticked)
        if clubs:
            sports_text += f" | Clubs: {clubs}" if sports_text else clubs

    # === TEMPLATE SWITCH - THIS IS THE ONLY NEW LOGIC ===
    grade_str = str(student.grade).upper() # e.g. "FORM 5A", "LOWER 6", "UPPER 6", "A-LEVEL"
    A_LEVEL_KEYS = ['FORM 5', 'FORM 6', 'LOWER 6', 'UPPER 6', 'A-LEVEL', 'A LEVEL', '5', '6']
    is_a_level = any(k in grade_str for k in ['5', '6', 'A-LEVEL', 'LOWER', 'UPPER'])

    if is_a_level or request.GET.get('template') == '2':
        template_path = 'C:/school_management_sys/kids/templates/word/Report_card_template_A_LEVEL.docx'
    else:
        template_path = 'C:/school_management_sys/kids/templates/word/Report_card_template.docx'

    def get_mark(index, field_name):
        if index < len(m_list):
            return getattr(m_list[index], field_name, '') or ''
        return ''

    def get_image_for_template(image_path, width=1.3):
        if image_path and image_path.exists():
            return InlineImage(doc, str(image_path), width=Inches(width))
        return ""

    photo_path = get_student_photo_path(student.grade, student.adm_no)
    stamp_path = get_stamp_path()

    print(f"[PHOTO CHECK] {photo_path} exists={photo_path.exists()}")
    print(f"[STAMP CHECK] {stamp_path} exists={stamp_path.exists()}")

    context = {
        # 1 to 15 - HEADER - WHERE MASTER STORED IT
        'photo': get_image_for_template(photo_path, 1.1),
        'stamp': get_image_for_template(stamp_path, 1.5),
        'student_name': f"{student.first_name} {student.last_name}",
        'birth_certificate_no': getattr(student, 'birth_cert_no', ''),
        'DOB': student.date_of_birth.strftime('%d/%m/%Y') if student.date_of_birth else '',
        'FORM': str(student.grade),
        'term': term,
        'year': str(term_year),
        'grade': str(student.grade),
        'position': str(correct_position), # <-- FROM MASTER LOGIC
        'total_students': str(total_students),
        'total_marks': str(correct_total), # add if you have placeholder
        'average': f"{correct_avg:.1f}",
        'ADDRESS': parent.address if parent else '',
        'PRIMARY_PARENT_NAME': parent.full_name if parent else '',
        'attendance_present': str(present_days),
        'attendance_possible': str(possible_dates),
        'subjects_passed': str(subjects_passed),
        'subjects_taken': str(len(m_list)),
        'activities': sports_text or ' - ',

    # 16 to 31 - EXAM - 4005 to 4025 - FROM Mark.current_exam_mark
    'exam_1': get_mark(0, 'current_exam_mark'),
    'exam_2': get_mark(1, 'current_exam_mark'),
    'exam_3': get_mark(2, 'current_exam_mark'),
    'exam_4': get_mark(3, 'current_exam_mark'),
    'exam_5': get_mark(4, 'current_exam_mark'),
    'exam_6': get_mark(5, 'current_exam_mark'),
    'exam_7': get_mark(6, 'current_exam_mark'),
    'exam_8': get_mark(7, 'current_exam_mark'),
    'exam_9': get_mark(8, 'current_exam_mark'),
    'exam_10': get_mark(9, 'current_exam_mark'),
    'exam_11': get_mark(10, 'current_exam_mark'),
    'exam_12': get_mark(11, 'current_exam_mark'),
    'exam_13': get_mark(12, 'current_exam_mark'),
    'exam_14': get_mark(13, 'current_exam_mark'),
    'exam_15': get_mark(14, 'current_exam_mark'),
    'exam_16': get_mark(15, 'current_exam_mark'),

    'project_1': get_mark(0, 'current_project_mark'),
    'project_2': get_mark(1, 'current_project_mark'),
    'project_3': get_mark(2, 'current_project_mark'),
    'project_4': get_mark(3, 'current_project_mark'),
    'project_5': get_mark(4, 'current_project_mark'),
    'project_6': get_mark(5, 'current_project_mark'),
    'project_7': get_mark(6, 'current_project_mark'),
    'project_8': get_mark(7, 'current_project_mark'),
    'project_9': get_mark(8, 'current_project_mark'),
    'project_10': get_mark(9, 'current_project_mark'),
    'project_11': get_mark(10, 'current_project_mark'),
    'project_12': get_mark(11, 'current_project_mark'),
    'project_13': get_mark(12, 'current_project_mark'),
    'project_14': get_mark(13, 'current_project_mark'),
    'project_15': get_mark(14, 'current_project_mark'),
    'project_16': get_mark(15, 'current_project_mark'),

        'avg_1': get_mark(0, 'current_avg'),
        'avg_2': get_mark(1, 'current_avg'),
        'avg_3': get_mark(2, 'current_avg'),
        'avg_4': get_mark(3, 'current_avg'),
        'avg_5': get_mark(4, 'current_avg'),
        'avg_6': get_mark(5, 'current_avg'),
        'avg_7': get_mark(6, 'current_avg'),
        'avg_8': get_mark(7, 'current_avg'),
        'avg_9': get_mark(8, 'current_avg'),
        'avg_10': get_mark(9, 'current_avg'),
        'avg_11': get_mark(10, 'current_avg'),
        'avg_12': get_mark(11, 'current_avg'),
        'avg_13': get_mark(12, 'current_avg'),
        'avg_14': get_mark(13, 'current_avg'),
        'avg_15': get_mark(14, 'current_avg'),
        'avg_16': get_mark(15, 'current_avg'),

        'GRADE_1': get_mark(0, 'current_grade'),
        'GRADE_2': get_mark(1, 'current_grade'),
        'GRADE_3': get_mark(2, 'current_grade'),
        'GRADE_4': get_mark(3, 'current_grade'),
        'GRADE_5': get_mark(4, 'current_grade'),
        'GRADE_6': get_mark(5, 'current_grade'),
        'GRADE_7': get_mark(6, 'current_grade'),
        'GRADE_8': get_mark(7, 'current_grade'),
        'GRADE_9': get_mark(8, 'current_grade'),
        'GRADE_10': get_mark(9, 'current_grade'),
        'GRADE_11': get_mark(10, 'current_grade'),
        'GRADE_12': get_mark(11, 'current_grade'),
        'GRADE_13': get_mark(12, 'current_grade'),
        'GRADE_14': get_mark(13, 'current_grade'),
        'GRADE_15': get_mark(14, 'current_grade'),
        'GRADE_16': get_mark(15, 'current_grade'),

        'remarks_1': get_mark(0, 'remarks'),
        'remarks_2': get_mark(1, 'remarks'),
        'remarks_3': get_mark(2, 'remarks'),
        'remarks_4': get_mark(3, 'remarks'),
        'remarks_5': get_mark(4, 'remarks'),
        'remarks_6': get_mark(5, 'remarks'),
        'remarks_7': get_mark(6, 'remarks'),
        'remarks_8': get_mark(7, 'remarks'),
        'remarks_9': get_mark(8, 'remarks'),
        'remarks_10': get_mark(9, 'remarks'),
        'remarks_11': get_mark(10, 'remarks'),
        'remarks_12': get_mark(11, 'remarks'),
        'remarks_13': get_mark(12, 'remarks'),
        'remarks_14': get_mark(13, 'remarks'),
        'remarks_15': get_mark(14, 'remarks'),
        'remarks_16': get_mark(15, 'remarks'),

        'initials_1': get_mark(0, 'trs_initials'),
        'initials_2': get_mark(1, 'trs_initials'),
        'initials_3': get_mark(2, 'trs_initials'),
        'initials_4': get_mark(3, 'trs_initials'),
        'initials_5': get_mark(4, 'trs_initials'),
        'initials_6': get_mark(5, 'trs_initials'),
        'initials_7': get_mark(6, 'trs_initials'),
        'initials_8': get_mark(7, 'trs_initials'),
        'initials_9': get_mark(8, 'trs_initials'),
        'initials_10': get_mark(9, 'trs_initials'),
        'initials_11': get_mark(10, 'trs_initials'),
        'initials_12': get_mark(11, 'trs_initials'),
        'initials_13': get_mark(12, 'trs_initials'),
        'initials_14': get_mark(12, 'trs_initials'),
        'initials_15': get_mark(14, 'trs_initials'),
        'initials_16': get_mark(15, 'trs_initials'),

        'teacher_comment': result.teacher_comment if result else '',
        'head_teacher_remark': result.head_teacher_comment if result else '',
        'NEXT_TERM_FEES': str(fee.total if fee else ''),
        'NEXT_TERM_OPEN_DATE': term_obj.end_date.strftime('%d %B %Y') if term_obj and term_obj.end_date else ''
    }

    doc.render(context)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer.read(),
                            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename=Report_{student.adm_no}_{term_name}.docx'
    return response

def export_master_marksheet_excel(request):
    class_name = request.GET.get('class', '').strip()
    year = request.GET.get('year', '2026').strip()
    term = request.GET.get('term', 'Term 1').strip()

    # Use same query as Master - no year filter
    students = Student.objects.filter(grade=class_name).order_by('last_name')
    # Get subjects from Marks for this class+term only - no year field
    subject_ids = Mark.objects.filter(student__grade=class_name, term=term).values_list('subject_id', flat=True).distinct()
    subjects = Subject.objects.filter(id__in=subject_ids).order_by('name')

    if not subjects.exists():
        subjects = Subject.objects.all().order_by('name')[:15]

    file_name = f"Mark Sheet {class_name} - {year} - {term}.xlsx".replace('/', '-')
    desktop_folder = Path.home() / "Desktop" / "Mark sheets"
    desktop_folder.mkdir(parents=True, exist_ok=True)
    file_path = desktop_folder / file_name

    wb = Workbook()
    ws = wb.active
    ws.title = f"{class_name}"

    ws['A1'] = f"Mark Sheet {class_name} - {year} - {term}"
    ws['A1'].font = Font(bold=True, size=14)

    # Header exactly as Master screen
    header = ['No', 'Adm No', 'Student Name']
    for subj in subjects:
        header.extend([f"{subj.name} Exam", f"{subj.name} Project", f"{subj.name} Avg", f"{subj.name} Grade"])
    ws.append([])
    ws.append(header)

    for idx, student in enumerate(students, start=1):
        row = [idx, getattr(student, 'adm_no', ''), f"{student.first_name} {student.last_name}"]
        for subj in subjects:
            # No year filter - only term
            m = Mark.objects.filter(student=student, subject=subj, term=term).first()
            if m:
                # use getattr so it never crashes if field name different
                exam = getattr(m, 'current_exam_mark', None) or getattr(m, 'exam_mark', '') or ''
                proj = getattr(m, 'current_project_mark', None) or getattr(m, 'project_mark', '') or ''
                avg = getattr(m, 'current_avg', None) or getattr(m, 'average', '') or ''
                grade = getattr(m, 'current_grade', None) or getattr(m, 'grade', '') or ''
                row.extend([exam, proj, avg, grade])
            else:
                row.extend(['', '', '', ''])
        ws.append(row)

    if file_path.exists():
        file_path.unlink()
    wb.save(file_path)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    from django.http import HttpResponse
    response = HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    return response


from django.shortcuts import get_object_or_404, render
from.models import Student, CourseWorkScore
from collections import defaultdict


def parent_coursework_weekly(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    # THIS IS THE FIX - Same as dashboard
    excluded_ids = list(SubjectEnrollment.objects.filter(
        student=student, is_active=False
    ).values_list('subject_id', flat=True))

    # Get weeks
    weeks = AcademicWeek.objects.all().order_by('week_number')
    weekly_data = {}

    for week in weeks:
        # Filter out excluded subjects HERE
        scores = CourseWorkScore.objects.filter(
            marksheet__week=week,
            student=student
        ).exclude(
            marksheet__subject_id__in=excluded_ids
        ).select_related('marksheet__subject')

        if scores.exists():  # Only show weeks where child has active subjects
            weekly_data[week] = scores

    return render(request, 'parent/coursework_weekly.html', {
        'student': student,
        'weekly_data': weekly_data
    })

from django.shortcuts import render
from .models import CourseWorkScore


def sports_class_select(request):
    grades = Student.objects.values_list('grade', flat=True).distinct().order_by('grade')

    return render(request, 'kids/sports_class_select.html', {'grades': grades})


@login_required
def sports_class_list(request, grade):
    students = Student.objects.filter(grade=grade).order_by('last_name', 'first_name')

    # LIST OF ALL SPORTS - THIS FIXES THE ERROR
    sports_list = [
        'soccer', 'netball', 'basketball', 'rugby', 'tennis', 'hockey', 'athletics',
        'high_jump', 'triple_jump', 'javelin', 'shot_put', 'hop_step_jump', 'swimming'
    ]
    sport_labels = {
        'soccer': 'Soccer', 'netball': 'Netball', 'basketball': 'Basketball', 'rugby': 'Rugby',
        'tennis': 'Tennis', 'hockey': 'Hockey', 'athletics': 'Athletics',
        'high_jump': 'HighJ', 'triple_jump': 'TripJ', 'javelin': 'Javelin',
        'shot_put': 'ShotPut', 'hop_step_jump': 'HSJ', 'swimming': 'Swim'
    }

    if request.method == 'POST':
        for student in students:
            activity, created = StudentActivity.objects.get_or_create(student=student)
            for sport in sports_list:
                setattr(activity, sport, request.POST.get(f'{sport}_{student.id}') == 'on')
            activity.clubs = request.POST.get(f'clubs_{student.id}', '')
            activity.save()
        return redirect('sports_class_select')

    # Attach existing activities to students
    for s in students:
        s.activity, _ = StudentActivity.objects.get_or_create(student=s)

    context = {
        'grade': grade,
        'students': students,
        'sports_list': sports_list,  # SEND TO TEMPLATE
        'sport_labels': sport_labels  # SEND TO TEMPLATE
    }
    return render(request, 'kids/sports_class_list.html', context)


def head_supervision_engine(request):
    from .models import Mark, Subject, Student, SubjectEnrollment, CourseWorkMarkSheet, CourseWorkScore
    import datetime, re

    today = datetime.date.today()

    # FIX: Get current term safely - handles both FK and CharField
    try:
        last_mark = Mark.objects.order_by('-id').first()
        if last_mark:
            current_term_obj = last_mark.term  # Could be object or string
            if hasattr(current_term_obj, 'id'):
                current_term = current_term_obj  # It's a Term object
                current_term_str = str(current_term_obj)
            else:
                current_term = str(current_term_obj)
                current_term_str = current_term
        else:
            current_term = None
            current_term_str = "Term 1"
    except:
        current_term = None
        current_term_str = "Term 1"

    current_week = today.isocalendar()[1]

    def get_grade_from_subj(subj):
        for f in ['grade', 'form', 'class_name']:
            v = getattr(subj, f, None)
            if v and str(v).strip():
                return str(v).strip()
        m = re.search(r'(Form\s*\d+\s*[A-Z]?)', str(subj), re.IGNORECASE)
        return m.group(1).strip() if m else ''


    # 1. ATTENDANCE
    attendance_board = []
    all_forms = [f for f in Student.objects.values_list('grade', flat=True).distinct() if f]
    for form_name in all_forms:
        total = Student.objects.filter(grade=form_name).count()
        marked = 0
        try:
            from .models import Attendance
            marked = Attendance.objects.filter(grade=form_name, date=today).count()
        except:
            pass
        percent = int((marked / total * 100) if total else 0)
        attendance_board.append({
            'grade': form_name, 'marked': marked, 'total': total,
            'percent': percent, 'status': 'OK' if percent >= 80 else 'MISSING'
        })
    # --- 2. MARKSHEET MONITOR ---
    all_subjects = Subject.objects.count()
    try:
        if current_term and hasattr(current_term, 'id'):
            subjects_with_marks = Mark.objects.filter(term=current_term).values('subject').distinct().count()
        else:
            subjects_with_marks = Mark.objects.filter(term__name=current_term_str).values(
                'subject').distinct().count() if current_term else 0
    except:
        subjects_with_marks = Mark.objects.values('subject').distinct().count()

    missing_sheets = all_subjects - subjects_with_marks

    subject_board = []
    for subj in Subject.objects.all():
        grade = get_grade_from_subj(subj)
        excluded_ids = list(
            SubjectEnrollment.objects.filter(subject=subj, is_active=False).values_list('student_id', flat=True))

        # Expected = students in class
        if grade:
            expected = Student.objects.filter(grade=grade).exclude(id__in=excluded_ids).count()
        else:
            expected = 0

        # FIX: Distinct students, not total Mark rows
        try:
            if current_term and hasattr(current_term, 'id'):
                base = Mark.objects.filter(subject=subj, term=current_term).exclude(student_id__in=excluded_ids)
            else:
                base = Mark.objects.filter(subject=subj).exclude(student_id__in=excluded_ids)
        except:
            base = Mark.objects.filter(subject=subj).exclude(student_id__in=excluded_ids)

        entered = base.values('student_id').distinct().count()

        if expected == 0:
            percent = 100
        else:
            percent = int(entered / expected * 100) if expected else 0
            if percent > 100:
                percent = 100

        subject_board.append(
            {'subject': str(subj), 'form': grade, 'entered': entered, 'expected': expected, 'percent': percent,
             'status': 'OK' if percent >= 80 else 'MISSING', 'subject_id': subj.id})


    # --- 3. COURSEWORK MONITOR - NOW READS CourseWorkScore ---
    coursework_board = []
    for subj in Subject.objects.all()[:50]:
        grade = get_grade_from_subj(subj)
        excluded_ids = list(
            SubjectEnrollment.objects.filter(subject=subj, is_active=False).values_list('student_id', flat=True))

        if grade:
            expected = Student.objects.filter(grade=grade).exclude(id__in=excluded_ids).count()
        else:
            expected = 0

        try:
            if current_term and hasattr(current_term, 'id'):
                sheets = CourseWorkMarkSheet.objects.filter(subject=subj, term=current_term)
            else:
                sheets = CourseWorkMarkSheet.objects.filter(subject=subj)
        except:
            sheets = CourseWorkMarkSheet.objects.filter(subject=subj)

        base_qs = CourseWorkScore.objects.filter(marksheet__in=sheets).exclude(student_id__in=excluded_ids)
        entered = base_qs.values('student_id').distinct().count()

        if expected == 0:
            percent = 100
        else:
            percent = int(entered / expected * 100) if expected else 0
            if percent > 100:
                percent = 100

        coursework_board.append(
            {'subject': str(subj), 'form': grade, 'entered': entered, 'expected': expected, 'percent': percent,
             'out_set': 'Yes' if sheets.exists() else 'No', 'subject_id': subj.id})

    context = {
        'today': today, 'current_term': current_term_str, 'current_week': current_week,
        'attendance_board': attendance_board, 'all_subjects': all_subjects,
        'sheets_this_week': subjects_with_marks, 'missing_sheets': missing_sheets,
        'subject_board': subject_board, 'coursework_board': coursework_board,
    }
    return render(request, 'kids/head_supervision.html', context)


def class_master_marksheet(request, grade):
    return class_register(request, grade)  # temp, until you build master sheet


def record_books_week_select(request, subject_id, *args, **kwargs):
    # The real view lives in academics app
    from academics.views import record_books_week_select as real_view
    return real_view(request, subject_id, *args, **kwargs)

from datetime import date, timedelta
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from django.http import HttpResponse

def official_register_excel(request, grade="FORM 3A", year="2026", term="3"):
    # === FIX: Use your real Term fields - name, start_date, end_date ===
    term_start = None
    term_end = None
    term_name = f"Term {term} {year}"

    try:
        from .models import Term
        terms_qs = Term.objects.all()
        # Find term where name contains term number and start_date year = year
        for t in terms_qs:
            if t.start_date and str(t.start_date.year) == str(year) and str(term) in t.name:
                term_start = t.start_date
                term_end = t.end_date
                term_name = t.name
                break

        # If not found, use current term
        if not term_start:
            cur = terms_qs.filter(is_current=True).first()
            if cur and cur.start_date:
                term_start = cur.start_date
                term_end = cur.end_date
                term_name = cur.name
    except Exception as e:
        print(f"Term lookup error: {e}")

    # Fallback if still no term - Term 3 2026 = 08 Sep to 05 Dec
    if not term_start:
        y = int(year) if str(year).isdigit() else 2026
        if str(term) == '3':
            term_start = date(y, 9, 8)
            term_end = date(y, 12, 5)
        elif str(term) == '2':
            term_start = date(y, 5, 5)
            term_end = date(y, 8, 2)
        else:
            term_start = date(y, 1, 10)
            term_end = date(y, 4, 5)

    # Generate 64 days Mon-Fri from term_start
    dates = []
    d = term_start
    while d <= term_end and len(dates) < 64:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)

    num_days = len(dates)
    weekdays = [dt.strftime("%a") for dt in dates]
    date_labels = [dt.strftime("%d/%m") for dt in dates]

    # Students
    students_qs = Student.objects.filter(grade=grade).order_by('last_name')
    girls = list(students_qs.filter(gender__icontains='F'))
    boys = list(students_qs.filter(gender__icontains='M'))
    if not girls and not boys:
        all_s = list(students_qs)
        girls = all_s[:len(all_s) // 2]
        boys = all_s[len(all_s) // 2:]

    wb = openpyxl.Workbook()
    ws_girls = wb.active
    ws_girls.title = "GIRLS PAGE 1"
    ws_boys = wb.create_sheet("BOYS PAGE 2")

    def build_sheet(ws, title, studs):
        ws['B1'] = "Ministry of Primary and Secondary Education"
        ws['B2'] = f"School: __________ District: __________ Province: __________"
        ws['B3'] = f"Form: {grade} Year: {year} {term_name} Teacher: __________"
        ws[
            'B4'] = f"{title} - {term_name} - {num_days} DAYS (14 WEEKS) - {term_start.strftime('%d %b %Y')} to {term_end.strftime('%d %b %Y')}"

        for r in [1, 2, 3, 4]:
            ws.cell(row=r, column=2).font = Font(bold=True, size=10)

        # Weeks
        for w in range(1, 15):
            col = 4 + (w - 1) * 5
            if col <= 3 + num_days:
                ws.cell(row=5, column=col).value = f"WEEK {w}"
                ws.merge_cells(start_row=5, start_column=col, end_row=5, end_column=min(col + 4, 3 + num_days))

        ws.cell(row=6, column=1).value = "#"
        ws.cell(row=6, column=2).value = "Adm No"
        ws.cell(row=6, column=3).value = "Student Name"
        for i, wd in enumerate(weekdays):
            ws.cell(row=6, column=4 + i).value = wd
        ws.cell(row=6, column=4 + num_days).value = "PRESENT"
        ws.cell(row=6, column=4 + num_days + 1).value = "ABSENT"
        ws.cell(row=6, column=4 + num_days + 2).value = "SICK"
        ws.cell(row=6, column=4 + num_days + 3).value = "TOTAL"

        ws.cell(row=7, column=1).value = "Counter"
        ws.cell(row=7, column=3).value = "DATES"
        for i, dl in enumerate(date_labels):
            ws.cell(row=7, column=4 + i).value = dl

        for r in [5, 6, 7]:
            for c in range(1, 4 + num_days + 5):
                cell = ws.cell(row=r, column=c)
                cell.alignment = Alignment(horizontal='center')
                if r == 5:
                    cell.fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
                    cell.font = Font(bold=True, color="FFFFFF", size=9)
                else:
                    cell.font = Font(bold=True, size=8)

        start_row = 8
        for idx, s in enumerate(studs, 1):
            row = start_row + idx - 1
            ws.cell(row=row, column=1).value = idx
            ws.cell(row=row, column=2).value = getattr(s, 'adm_no', f"T{idx:03d}")
            ws.cell(row=row, column=3).value = getattr(s, 'full_name', f"{s.first_name} {s.last_name}")
            for j, dt in enumerate(dates):
                att = Attendance.objects.filter(student=s, date=dt).first()
                val = "/" if att and att.status == "Present" else "O" if att and att.status == "Absent" else "S" if att and att.status == "Sick" else ""
                ws.cell(row=row, column=4 + j).value = val
            # Totals per student with formulas
            ws.cell(row=row, column=4 + num_days).value = f'=COUNTIF(D{row}:{get_column_letter(3 + num_days)}{row},"/")'
            ws.cell(row=row,
                    column=4 + num_days + 1).value = f'=COUNTIF(D{row}:{get_column_letter(3 + num_days)}{row},"O")'
            ws.cell(row=row,
                    column=4 + num_days + 2).value = f'=COUNTIF(D{row}:{get_column_letter(3 + num_days)}{row},"S")'
            ws.cell(row=row,
                    column=4 + num_days + 3).value = f'=SUM({get_column_letter(4 + num_days)}{row}:{get_column_letter(4 + num_days + 2)}{row})'

        last = start_row + len(studs) - 1
        r_att = last + 1
        r_abs = last + 2
        r_sick = last + 3
        r_poss = last + 4

        ws.cell(row=r_att, column=3).value = "Actual Attendance"
        ws.cell(row=r_abs, column=3).value = "Actual Absenteeism"
        ws.cell(row=r_sick, column=3).value = "Actual Sick"
        ws.cell(row=r_poss, column=3).value = "Possible Attendance"
        for r in [r_att, r_abs, r_sick, r_poss]:
            ws.cell(row=r, column=3).font = Font(bold=True)

        for j in range(num_days):
            col = 4 + j
            cl = get_column_letter(col)
            ws.cell(row=r_att, column=col).value = f'=COUNTIF({cl}{start_row}:{cl}{last},"/")'
            ws.cell(row=r_abs, column=col).value = f'=COUNTIF({cl}{start_row}:{cl}{last},"O")'
            ws.cell(row=r_sick, column=col).value = f'=COUNTIF({cl}{start_row}:{cl}{last},"S")'
            ws.cell(row=r_poss, column=col).value = f'=SUM({cl}{r_att}:{cl}{r_sick})'

        # Totals - Green 31, Yellow 6, Grey 4, Blue 37
        ws.cell(row=r_att, column=4 + num_days).value = f'=SUM(D{r_att}:{get_column_letter(3 + num_days)}{r_att})'
        ws.cell(row=r_abs,
                column=4 + num_days + 1).value = f'=SUM({get_column_letter(4 + num_days + 1)}{start_row}:{get_column_letter(4 + num_days + 1)}{last})'
        ws.cell(row=r_sick,
                column=4 + num_days + 2).value = f'=SUM({get_column_letter(4 + num_days + 2)}{start_row}:{get_column_letter(4 + num_days + 2)}{last})'
        ws.cell(row=r_poss,
                column=4 + num_days + 3).value = f'={get_column_letter(4 + num_days)}{r_att}+{get_column_letter(4 + num_days + 1)}{r_abs}+{get_column_letter(4 + num_days + 2)}{r_sick}'

        # Colours as you marked
        ws.cell(row=r_att, column=4 + num_days).fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE",
                                                                   fill_type="solid")
        ws.cell(row=r_abs, column=4 + num_days + 1).fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C",
                                                                       fill_type="solid")
        ws.cell(row=r_sick, column=4 + num_days + 2).fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9",
                                                                        fill_type="solid")
        ws.cell(row=r_poss, column=4 + num_days + 3).fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE",
                                                                        fill_type="solid")

        ws.column_dimensions['B'].width = 32
        ws.column_dimensions['C'].width = 26
        ws.freeze_panes = 'D8'

        ws.append([])
        ws.append(["Class Teacher Signature: ________________ Date: ______"])
        ws.append(["Head Signature: ________________ Date: ______   School Stamp:"])

    build_sheet(ws_girls, "GIRLS PAGE 1", girls)
    build_sheet(ws_boys, "BOYS PAGE 2", boys)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={grade}_{year}_Term{term}_BALANCED.xlsx'
    wb.save(response)
    return response
