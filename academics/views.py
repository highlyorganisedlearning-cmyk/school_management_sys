from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.forms import modelformset_factory
from kids.models import Student, Subject, AcademicWeek, CourseWorkMarkSheet, CourseWorkScore, Term
from .forms import CourseWorkScoreForm, CourseWorkMarkSheetForm
from datetime import timedelta
from kids.models import CourseWorkMarkSheet, CourseWorkScore



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

def record_books_class_select(request):
    # Get unique grades from subjects
    grades = Subject.objects.values_list('grade', flat=True).distinct().order_by('grade')
    return render(request, 'academics/rb_class_select.html', {'grades': grades})


def record_books_subject_select(request, grade):
    subjects = Subject.objects.filter(grade=grade).order_by('name')
    return render(request, 'academics/rb_subject_select.html', {'subjects': subjects, 'grade': grade})


def record_books_week_select(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    ensure_weeks_for_term(subject.term)
    weeks = AcademicWeek.objects.filter(term=subject.term).order_by('week_number')
    return render(request, 'academics/rb_week_select.html', {'weeks': weeks, 'subject': subject})


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





