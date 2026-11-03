from django.db import models
from datetime import date
from django.db.models.signals import post_save
from django.dispatch import receiver
from fractions import Fraction

FEE_TYPES = [
    ('levy', 'Levy'),
    ('building_fund', 'Building Fund'),
    ('sports_fee', 'Sports Fee'),
    ('tuition_fee', 'Tuition Fee'),
    ('bus_levy', 'Bus Levy'),
    ('practical', 'Practical'),
    ('projects', 'Projects'),
    ('other', 'Other'),
]

class Expenditure(models.Model):
    fee_type = models.CharField(max_length=50, choices=FEE_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.fee_type} - ${self.amount}"


class Parent(models.Model):
    RELATIONSHIP_CHOICES = [
        ('MOTHER', 'Mother'),
        ('FATHER', 'Father'),
        ('GUARDIAN', 'Guardian'),
        ('OTHER', 'Other'),
    ]

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    relationship = models.CharField(max_length=10, choices=RELATIONSHIP_CHOICES)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} - {self.phone}"

class StudentParent(models.Model): # This must come before Student too
    student = models.ForeignKey('Student', on_delete=models.CASCADE) # Use 'Student' as string to avoid issues
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    is_primary_contact = models.BooleanField(default=False)

    class Meta:
        unique_together = ['student', 'parent']

    def __str__(self):
        return f"{self.student} - {self.parent}"

class Student(models.Model):
    # Core ID - this is your Admission No now
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    adm_no = models.CharField(max_length=20, unique=True)
    grade = models.CharField(max_length=10)
    fee_required = models.DecimalField(max_digits=10, decimal_places=2, default=300.00)
    date_added = models.DateTimeField(auto_now_add=True)
    #head_comment = models.TextField(blank=True, null=True, default='')
    parent_phone = models.CharField(max_length=15, blank=True, null=True)

    # Extra info
    date_of_birth = models.DateField(null=True, blank=True)
    birth_cert_no = models.CharField(max_length=50, blank=True, null=True)  # <-- ADD THIS
    gender = models.CharField(max_length=10, choices=[('M','Male'),('F','Female')], null=True, blank=True)
    date_joined = models.DateField(auto_now_add=True, null=True, blank=True)

    # Parent Relationship
    parents = models.ManyToManyField(Parent, through='StudentParent', blank=True)

    def save(self, *args, **kwargs):
        if not self.adm_no:
            last = Student.objects.order_by('-id').first()
            num = int(last.adm_no[1:]) + 1 if last and last.adm_no.startswith('T') else 1
            self.adm_no = f'T{num:03d}'
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.adm_no} - {self.full_name}"


class FeeStructure(models.Model):
    grade = models.CharField(max_length=20, unique=True)  # "Form 1", "Grade 1"
    levy = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    building_fund = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sports_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bus_levy = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    practical = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    projects = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def total(self):
        return (self.levy + self.building_fund + self.sports_fee +
                self.tuition_fee + self.bus_levy + self.practical +
                self.projects + self.other)

    def __str__(self):
        return f"{self.grade} - Total: ${self.total}"

class Attendance(models.Model):
    ATTENDANCE_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Sick', 'Sick'),
        ('Late', 'Late'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    #date = models.DateField(auto_now_add=True)
    date = models.DateField(default=date.today)
    status = models.CharField(max_length=10, choices=ATTENDANCE_CHOICES, default='Present')
    grade = models.CharField(max_length=50)  # snapshot of grade on that day

    def __str__(self):
        return f"{self.student.adm_no} - {self.date} - {self.status}"

class Subject(models.Model):
    name = models.CharField(max_length=50)  # "Mathematics", "English"
    grade = models.CharField(max_length=20)  # "Grade 1"
    order = models.IntegerField(default=0)  # <-- YOU MISSED THIS, ADD IT
    teacher = models.ForeignKey('Teacher', on_delete=models.SET_NULL, null=True, blank=True)
    term = models.ForeignKey('Term', on_delete=models.CASCADE, null=True, blank=True)
    expected_students = models.IntegerField(default=0,
                                            help_text="How many students do this subject? 0 = auto count whole class")
    class Meta:
        unique_together = ('name', 'grade', 'term')
        ordering = ['order']  # now this will work because order exists

    def __str__(self):
        return f"{self.grade} - {self.name} ({self.order})"


class Term(models.Model):
    name = models.CharField(max_length=20, unique=True)  # "Term 1 2026", "Term 2 2026"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Teacher(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Mark(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    term = models.CharField(max_length=20, default='Term 1')
    average = models.DecimalField(max_digits=5, decimal_places=0, null=True, blank=True)
    grade = models.CharField(max_length=10, null=True, blank=True)
    admission_avg = models.DecimalField(max_digits=5, decimal_places=0, null=True, blank=True)
    previous_avg = models.DecimalField(max_digits=5, decimal_places=0, null=True, blank=True)
    current_exam_mark = models.DecimalField(max_digits=5, decimal_places=0, null=True, blank=True)
    current_project_mark = models.DecimalField(max_digits=5, decimal_places=0, null=True, blank=True)
    current_avg = models.DecimalField(max_digits=5, decimal_places=0, null=True, blank=True)
    current_grade = models.CharField(max_length=2, null=True, blank=True)
    trend = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    remarks = models.CharField(max_length=100, null=True, blank=True)
    trs_initials = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        unique_together = ('student', 'subject', 'term') # so each student has 1 mark per subject per term


class StudentTermResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    grade = models.CharField(max_length=20)
    term = models.CharField(max_length=20)  # 'Term 1', 'Month 1', etc
    year = models.IntegerField()

    total_marks = models.DecimalField(max_digits=6, decimal_places=0, default=0)
    position = models.IntegerField(null=True, blank=True)

    teacher_comment = models.TextField(blank=True)  # ADD THIS
    head_teacher_comment = models.TextField(blank=True)
    activity = models.TextField(blank=True, default="")  # <-- ADD THIS
    comment_choice = models.IntegerField(null=True, blank=True)  # stores 1-25

    class Meta:
        unique_together = ('student', 'term', 'year')

    def __str__(self):
        return f"{self.student} - {self.term} {self.year}"


class HeadComment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    grade = models.CharField(max_length=20)
    term = models.CharField(max_length=20)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'grade', 'term')  # one comment per student per term

    def __str__(self):
        return f"{self.student.first_name} - {self.term} Comment"


class AcademicWeek(models.Model):
    term = models.ForeignKey('Term', on_delete=models.CASCADE)
    week_number = models.IntegerField()  # 1 to 13
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        unique_together = ['term', 'week_number']


class CourseWorkMarkSheet(models.Model):
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE)
    term = models.ForeignKey('Term', on_delete=models.CASCADE)
    week = models.ForeignKey('AcademicWeek', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    # Out of marks - editable every week
    out_ex1 = models.CharField(max_length=6, null=True, blank=True, default='')
    out_ex2 = models.CharField(max_length=6, null=True, blank=True, default='')
    out_ex3 = models.CharField(max_length=6, null=True, blank=True, default='')
    out_ex4 = models.CharField(max_length=6, null=True, blank=True, default='')
    out_ex5 = models.CharField(max_length=6, null=True, blank=True, default='')
    out_ex6 = models.CharField(max_length=6, null=True, blank=True, default='')
    out_ex7 = models.CharField(max_length=6, null=True, blank=True, default='')
    out_test1 = models.CharField(max_length=6, null=True, blank=True, default='')
    out_test2 = models.CharField(max_length=6, null=True, blank=True, default='')
    date_ex1 = models.DateField(null=True, blank=True)
    date_ex2 = models.DateField(null=True, blank=True)
    date_ex3 = models.DateField(null=True, blank=True)
    date_ex4 = models.DateField(null=True, blank=True)
    date_ex5 = models.DateField(null=True, blank=True)
    date_ex6 = models.DateField(null=True, blank=True)
    date_ex7 = models.DateField(null=True, blank=True)
    date_test1 = models.DateField(null=True, blank=True)
    date_test2 = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ['subject', 'week']

class CourseWorkScore(models.Model):
    marksheet = models.ForeignKey(CourseWorkMarkSheet, on_delete=models.CASCADE, related_name='scores')
    student = models.ForeignKey('Student', on_delete=models.CASCADE)

    # Changed to CharField to allow 15, A, S
    ex1 = models.CharField(max_length=6, null=True, blank=True)
    ex2 = models.CharField(max_length=6, null=True, blank=True)
    ex3 = models.CharField(max_length=6, null=True, blank=True)
    ex4 = models.CharField(max_length=6, null=True, blank=True)
    ex5 = models.CharField(max_length=6, null=True, blank=True)
    ex6 = models.CharField(max_length=6, null=True, blank=True)
    ex7 = models.CharField(max_length=6, null=True, blank=True)
    test1 = models.CharField(max_length=6, null=True, blank=True)
    test2 = models.CharField(max_length=6, null=True, blank=True)

    class Meta:
        unique_together = ['marksheet', 'student'] # FIXED: 1 student per marksheet


    @property
    def p1_raw(self):
        return f"{self.ex1}/{self.marksheet.out_ex1}"  # 25/100

    @property
    def p2_raw(self):
        return f"{self.ex2}/{self.marksheet.out_ex2}"  # 25/100

    @property
    def p3_raw(self):
        return f"{self.ex3}/{self.marksheet.out_ex3}"  # 25/100

    @property
    def p4_raw(self):
        return f"{self.ex4}/{self.marksheet.out_ex4}"  # 25/100

    @property
    def p5_raw(self):
        return f"{self.ex5}/{self.marksheet.out_ex5}"  # 25/100

    @property
    def p6_raw(self):
        return f"{self.ex6}/{self.marksheet.out_ex6}"  # 25/100

    @property
    def p7_raw(self):
        return f"{self.ex7}/{self.marksheet.out_ex7}"  # 25/100

    @property
    def p8_raw(self):
        return f"{self.test1}/{self.marksheet.out_test1}"  # 25/100

    @property
    def p9_raw(self):
        return f"{self.test2}/{self.marksheet.out_test2}"  # 25/100

    @property
    def weekly_total1(self):
        scores = []
        for s in [self.ex1, self.ex2, self.ex3, self.ex4, self.ex5, self.ex6, self.ex7, self.test1, self.test2]:
            if s and s.upper() not in ['A', 'S']:
                try:
                     Fraction(self.ex1, self.marksheet.out_ex1)
                except:
                    pass
        return 0 if scores else (self.ex1, self.marksheet.out_ex1)

    @property
    def weekly_average_percent(self):
        total_out = sum([
            self.marksheet.out_ex1 or 0, self.marksheet.out_ex2 or 0, self.marksheet.out_ex3 or 0,
            self.marksheet.out_ex4 or 0, self.marksheet.out_ex5 or 0, self.marksheet.out_ex6 or 0,
            self.marksheet.out_ex7 or 0, self.marksheet.out_test1 or 0, self.marksheet.out_test2 or 0
        ])
        if total_out == 0: return 0
        return round((self.weekly_total / total_out) * 100, 1)



@receiver(post_save, sender=Subject)
def create_coursework_marksheets(sender, instance, created, **kwargs):
    if created:
        term = instance.term
        weeks = AcademicWeek.objects.filter(term=term)
        for week in weeks:
            CourseWorkMarkSheet.objects.create(
                subject=instance,
                teacher=instance.teacher,
                term=term,
                week=week
            )

class StudentMark(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    term = models.ForeignKey('Term', on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)

    admission_avg = models.FloatField(null=True, blank=True)
    previous_avg = models.FloatField(null=True, blank=True)
    current_avg = models.FloatField(null=True, blank=True)

    trend = models.FloatField(null=True, blank=True)
    remarks = models.CharField(max_length=100, null=True, blank=True) # stores 'excellent 1' or 'Dead' etc
    remark_locked = models.BooleanField(default=False) # optional: to prevent changing R/Z

    class Meta:
        unique_together = ['student', 'term', 'subject']


class StudentActivity(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='activities')

    # SPORTS - Checkbox style
    soccer = models.BooleanField(default=False)
    netball = models.BooleanField(default=False)
    basketball = models.BooleanField(default=False)
    rugby = models.BooleanField(default=False)
    tennis = models.BooleanField(default=False)
    hockey = models.BooleanField(default=False)
    athletics = models.BooleanField(default=False)
    high_jump = models.BooleanField(default=False)
    triple_jump = models.BooleanField(default=False)
    javelin = models.BooleanField(default=False)
    shot_put = models.BooleanField(default=False)
    hop_step_jump = models.BooleanField(default=False)
    swimming = models.BooleanField(default=False)

    # CLUBS - Text field so we can add more later
    clubs = models.TextField(blank=True, null=True, help_text="Comma separated: Drama, Chess, SU, Marimba, Science etc")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.full_name} Activities"

    def get_sports_list(self):
        sports = []
        for field in ['soccer', 'netball', 'basketball', 'rugby', 'tennis', 'hockey', 'athletics', 'high_jump',
                      'triple_jump', 'javelin', 'shot_put', 'hop_step_jump', 'swimming']:
            if getattr(self, field):
                sports.append(field.replace('_', ' ').title())
        return ", ".join(sports) if sports else "-"


class SchoolSettings(models.Model): # if you want it in kids instead, keep academics empty
    register_check_time = models.TimeField(default="10:00")


class SubjectEnrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    form_class = models.CharField(max_length=20) # e.g. "Form 3A"
    is_active = models.BooleanField(default=True) # False = excluded

    class Meta:
        unique_together = ('student','subject')


