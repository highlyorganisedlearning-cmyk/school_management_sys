from django.urls import path
from . import views
from.views import parent_coursework_weekly, login_required
from django.urls import path
from . import views
from academics import views as acad_views

urlpatterns = [
    path('', views.main_menu, name='main_menu'),
    path('register/', views.school_register, name='school_register'),
    path('fees/', views.school_fees, name='school_fees'),
    path('class/<str:grade>/', views.class_register, name='class_register'),
    path('report-cards/', views.report_cards, name='report_cards'),
    path('report-card/<int:student_id>/<str:term>/', views.download_report_card, name='download_report_card'),
    path('reports/<str:grade>/', views.grade_subjects, name='grade_subjects'),
    path('add-student/', views.add_student, name='add_student'),
    path('marksheet/<str:grade>/<int:subject_id>/', views.marksheet, name='marksheet'),
    path('master-marksheet/<str:grade>/', views.master_marksheet, name='master_marksheet'),
    path('student-summaries-cards/', views.student_summaries_cards, name='student_summaries'),
    path('generate_professional_reports/<str:grade>/', views.generate_professional_reports,
         name='generate_professional_reports'),
    path('comment/<int:student_id>/', views.head_comments, name='head_comments'),
    path('class-teacher-comment/<int:student_id>/', views.class_teacher_comments, name='class_teacher_comments'),
    path('report/download/<int:student_id>/<str:term_name>/<int:year>/', views.download_report_card, name='download_report'),
    path('report-card/<int:student_id>/<str:term>/', views.download_report_card, name='download_report'),
    path('parent/', views.parent_dashboard, name='parent_dashboard'),
    path('parent/report/<int:student_id>/<str:term>/', views.download_report_card, name='download_report_card'),
    path('report/<int:student_id>/', views.download_report_card, name='download_report_card'),
    path('parent/', views.parent_dashboard, name='parent_dashboard'),
    path('export-marksheet/', views.export_master_marksheet_excel, name='export_marksheet_excel'),
    path('parent/student/<int:student_id>/coursework-weekly/', parent_coursework_weekly,
         name='parent_coursework_weekly'),
    path('sports/', views.sports_class_select, name='sports_class_select'),
    path('sports/<str:grade>/', views.sports_class_list, name='sports_class_list'),
    path('subject-comments/<int:student_id>/<int:term_id>/<int:subject_id>/',login_required(views.subject_teacher_comments), name='subject_teacher_comments'),
    path('head/supervision/', views.head_supervision_engine, name='head_supervision'),
    path('class/<str:grade>/', views.class_register, name='class_register'),
    path('class/<str:grade>/master/', views.class_master_marksheet, name='class_master_marksheet'), # ADD THIS
    path('coursework/<int:subject_id>/', views.record_books_week_select, name='coursework_shortcut'), # ADD THIS for V11
    path('record-books/<int:subject_id>/weeks/', acad_views.record_books_week_select, name='record_books_week_select'),
    path('coursework/<int:subject_id>/', acad_views.record_books_week_select, name='coursework_shortcut'),
    #path('ministry/register/', views.ministry_register, name='ministry_register_all'),
    #path('ministry/register/<str:grade>/', views.ministry_register, name='ministry_register'),
    #path('register/official/<str:grade>/', views.official_register_docx, name='official_register_docx'),
    path('register/', views.school_register, name='school_register'),
    path('register/excel/<str:grade>/<str:year>/<str:term>/', views.official_register_excel,
         name='official_register_excel'),

]










