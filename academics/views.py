from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.forms import modelformset_factory
from kids.models import Student, Subject, AcademicWeek, CourseWorkMarkSheet, CourseWorkScore, Term, SubjectEnrollment
from .forms import CourseWorkScoreForm, CourseWorkMarkSheetForm
from datetime import timedelta, date
from kids.models import CourseWorkMarkSheet, CourseWorkScore
from django.contrib.auth.decorators import login_required

def ensure_weeks_for_term(term):
    # School week: Monday to Sunday - includes weekends
    if not term.start_date or not term.end_date:
        return

    # Find first Monday
    # Monday = 0, Sunday = 6
    if term.start_date.weekday() == 6:
        # Term starts on Sunday - that Sunday belongs to last week
        # Week 1 starts next day, Monday
        first_monday = term.start_date + timedelta(days=1)
    else:
        # Mon to Sat - Week 1 starts on Monday of that week
        first_monday = term.start_date - timedelta(days=term.start_date.weekday())

    week_number = 1
    week_start = first_monday

    while week_start <= term.end_date:
        week_end = week_start + timedelta(days=6)  # Sunday
        if week_end > term.end_date:
            week_end = term.end_date

        AcademicWeek.objects.get_or_create(
            term=term,
            week_number=week_number,
            defaults={'start_date': week_start, 'end_date': week_end}
        )

        week_number += 1
        week_start = week_start + timedelta(days=7)  # next Monday

@login_required
def record_books_class_select(request):
    # Get unique grades from subjects
    grades = Subject.objects.values_list('grade', flat=True).distinct().order_by('grade')
    return render(request, 'academics/rb_class_select.html', {'grades': grades})

@login_required
def record_books_subject_select(request, grade):
    subjects = Subject.objects.filter(grade=grade).order_by('name')
    return render(request, 'academics/rb_subject_select.html', {'subjects': subjects, 'grade': grade})


def record_books_week_select(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    ensure_weeks_for_term(subject.term)
    weeks = AcademicWeek.objects.filter(term=subject.term).order_by('week_number')
    today = date.today()
    current_week_id = None
    for w in weeks:
        if w.start_date and w.end_date and w.start_date <= today <= w.end_date:
            current_week_id = w.id
            break
    return render(request, 'academics/rb_week_select.html', {
        'weeks': weeks,
        'subject': subject,
        'today': today,
        'current_week_id': current_week_id,
    })

@login_required
def coursework_marksheet(request, subject_id, week_id):
    subject = get_object_or_404(Subject, id=subject_id)
    week = get_object_or_404(AcademicWeek, id=week_id)

    marksheet, created = CourseWorkMarkSheet.objects.get_or_create(
        subject=subject, week=week,
        defaults={'teacher': subject.teacher, 'term': subject.term}
    )

    students = Student.objects.filter(grade=subject.grade).order_by('last_name', 'first_name')
    for student in students:
        CourseWorkScore.objects.get_or_create(marksheet=marksheet, student=student)

    ScoreFormSet = modelformset_factory(CourseWorkScore, form=CourseWorkScoreForm, extra=0, can_delete=False)

    if request.method == 'POST' and 'subject_id' not in request.POST:  # Save Marks, not Exclude
        marksheet_form = CourseWorkMarkSheetForm(request.POST, instance=marksheet)
        formset = ScoreFormSet(request.POST,
                               queryset=marksheet.scores.select_related('student').order_by('student__last_name'))
        if marksheet_form.is_valid() and formset.is_valid():
            marksheet_form.save()
            instances = formset.save(commit=False)
            for instance in instances:
                instance.marksheet = marksheet
                instance.save()
            messages.success(request, f'✅ Saved: {subject.name} Week {week.week_number}')
            return redirect('coursework_marksheet', subject_id, week_id)
    else:
        marksheet_form = CourseWorkMarkSheetForm(instance=marksheet)
        formset = ScoreFormSet(queryset=marksheet.scores.select_related('student').order_by('student__last_name'))

    # --- EXCLUDE LOGIC FOR DISPLAY ONLY ---
    enrollments = SubjectEnrollment.objects.filter(subject=subject)
    enroll_map = {e.student_id: e.is_active for e in enrollments}
    for form in formset:
        sid = form.instance.student_id
        is_active = enroll_map.get(sid, True)
        form.instance.is_excluded_flag = not is_active

    date_fields = [f for f in marksheet_form if 'date' in f.name]
    out_fields = [f for f in marksheet_form if 'out_' in f.name]

    # FIX: SEND all_grades to template!
    all_grades = Student.objects.values_list('grade', flat=True).distinct().order_by('grade')

    return render(request, 'academics/Coursework_marksheet.html', {
        'formset': formset,
        'marksheet_form': marksheet_form,
        'date_fields': date_fields,
        'out_fields': out_fields,
        'subject': subject,
        'week': week,
        'all_grades': all_grades,  # <-- THIS WAS MISSING!
    })

@login_required
def coursework_term_summary(request):
    year = request.GET.get('year', '2026')
    term_name = request.GET.get('term', 'Term 3')
    grade = request.GET.get('grade', 'Form 3A')
    subject_name = request.GET.get('subject', 'COMBINED SCIENCE')


    import re
    term_number = re.search(r'\d+', term_name)
    term_number = term_number.group(0).lstrip('0') if term_number else term_name


    sheets = CourseWorkMarkSheet.objects.filter(
        subject__name=subject_name,
        subject__grade=grade,
        term__name__icontains=f"Term {term_number}",
        term__start_date__year=year,
    ).order_by('week__week_number')

    students = Student.objects.filter(grade=grade).order_by('last_name', 'first_name')

    weeks_data = []
    for sheet in sheets:
        tasks = []
        # Your exact fields Cap: date_ex1...date_ex7, date_test1, date_test2
        # and ex1...ex7, test1, test2
        for label, date_field, out_field in [
            ('Ex1', 'date_ex1', 'out_ex1'),
            ('Ex2', 'date_ex2', 'out_ex2'),
            ('Ex3', 'date_ex3', 'out_ex3'),
            ('Ex4', 'date_ex4', 'out_ex4'),
            ('Ex5', 'date_ex5', 'out_ex5'),
            ('Ex6', 'date_ex6', 'out_ex6'),
            ('Ex7', 'date_ex7', 'out_ex7'),
            ('Test1', 'date_test1', 'out_test1'),
            ('Test2', 'date_test2', 'out_test2'),
        ]:
            # Only show if teacher entered a date OR an out_of for that task
            d = getattr(sheet, date_field, None)
            o = getattr(sheet, out_field, None)
            if d or o:
                tasks.append({'label': label, 'date': d, 'out_of': o})

        scores = {s.student_id: s for s in CourseWorkScore.objects.filter(marksheet=sheet)}

        rows = []
        for st in students:
            sc = scores.get(st.id)
            cells = []
            for t in tasks:
                if not sc:
                    cells.append('')
                else:
                    field = t['label'].lower()  # Ex1 -> ex1, Test1 -> test1
                    val = getattr(sc, field, '')
                    out = t['out_of']
                    if val == '' or val is None:
                        cells.append('')
                    elif out:
                        cells.append(f"{val}/{out}")
                    else:
                        cells.append(str(val))
            rows.append({'student': st, 'cells': cells})


        weeks_data.append({
            'week_no': sheet.week.week_number if hasattr(sheet.week, 'week_number') else sheet.week_id,
            'tasks': tasks,
            'rows': rows,
        })

    all_grades = list(Subject.objects.values_list('grade', flat=True).distinct().order_by('grade'))

    if grade:
            all_subjects = list(
            Subject.objects.filter(grade=grade).values_list('name', flat=True).distinct().order_by('name'))
    else:
        all_subjects = list(Subject.objects.values_list('name', flat=True).distinct().order_by('name'))
    all_terms = list(Term.objects.values_list('name', flat=True).order_by('start_date'))
    all_years = list(Term.objects.dates('start_date', 'year').values_list('start_date__year', flat=True))

    all_years = sorted(set([t.start_date.year for t in Term.objects.all()]))

    return render(request, '/school_management_sys/kids/templates/academics/coursework_term_summary.html', {
        'year': year, 'term_name': term_name, 'grade': grade,
        'subject_name': subject_name, 'weeks_data': weeks_data,
        'all_grades': all_grades, 'all_subjects': all_subjects,
        'all_terms': all_terms, 'all_years': all_years,
        })


from django.shortcuts import redirect
from kids.models import Student, Subject, SubjectEnrollment

def toggle_enrollment(request, student_id, subject_id):
    try:
        student = Student.objects.get(id=student_id)
        subject = Subject.objects.get(id=subject_id)
    except:
        return redirect(request.META.get('HTTP_REFERER', '/'))

    enroll, created = SubjectEnrollment.objects.get_or_create(
        student=student,
        subject=subject,
        defaults={'is_active': False}  # <-- CHANGE to False, so first click = Exclude
    )
    if not created:
        enroll.is_active = not enroll.is_active
        enroll.save()

    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def exclude_whole_class(request):
    if request.method == "POST":
        subject_id = request.POST.get('subject_id')
        grade = request.POST.get('grade', '').strip()
        if not grade or not subject_id:
            messages.error(request, "Select a Class first!")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        students = Student.objects.filter(grade=grade)
        count = 0
        for stud in students:
            obj, created = SubjectEnrollment.objects.get_or_create(
                student=stud, subject_id=subject_id,
                defaults={'is_active': False}
            )
            if not created:
                obj.is_active = False
                obj.save()
            count += 1

        messages.success(request,
                         f"🚫 Excluded {count} learners of {grade} from {Subject.objects.get(id=subject_id)} - Master will now show 100%!")
    return redirect(request.META.get('HTTP_REFERER', '/'))





