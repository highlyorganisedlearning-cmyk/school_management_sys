from django.contrib import admin
from.models import (
    FeeStructure, Student, Attendance, Subject, Mark, StudentTermResult, Term, Teacher, AcademicWeek,
    CourseWorkMarkSheet, CourseWorkScore, Parent, StudentParent
)


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_current', 'start_date', 'end_date')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name']
    search_fields = ['first_name', 'last_name']

@admin.register(AcademicWeek)
class AcademicWeekAdmin(admin.ModelAdmin):
    list_display = ['term', 'week_number', 'start_date', 'end_date']
    list_filter = ['term']
    ordering = ['term', 'week_number']

@admin.register(CourseWorkMarkSheet)
class CourseWorkMarkSheetAdmin(admin.ModelAdmin):
    list_display = ['subject', 'week', 'teacher', 'term', 'created_at']
    list_filter = ['term', 'subject__grade', 'teacher']

@admin.register(CourseWorkScore)
class CourseWorkScoreAdmin(admin.ModelAdmin):
    list_display = ['marksheet', 'student']
    list_filter = ['marksheet__term', 'marksheet__subject']


admin.site.register(Attendance)
admin.site.register(Mark)
admin.site.register(StudentTermResult)


class StudentParentInline(admin.TabularInline):
    model = StudentParent
    extra = 1

class StudentParentInlineForParent(admin.TabularInline):
    model = StudentParent
    extra = 1

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['adm_no', 'full_name', 'grade', 'date_joined']
    list_filter = ['grade', 'gender']
    search_fields = ['first_name', 'last_name', 'adm_no']
    readonly_fields = ['adm_no']
    inlines = [StudentParentInline]

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'relationship']
    search_fields = ['full_name', 'phone']
    inlines = [StudentParentInlineForParent]

@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display = ['student', 'parent', 'is_primary_contact']
    list_filter = ['is_primary_contact']


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    # Your model uses 'grade' and individual fees, not 'term', 'fee_type', 'amount'
    list_display = ('grade', 'tuition_fee', 'levy', 'building_fund', 'sports_fee', 'bus_levy', 'total')
    list_filter = ('grade',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade', 'order', 'teacher', 'term')
    list_editable = ('order',)
    ordering = ('order',)

