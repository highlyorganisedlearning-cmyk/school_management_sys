from django.urls import path
from . import views

urlpatterns = [
    path('record-books/', views.record_books_class_select, name='record_books_class_select'),
    path('record-books/grade/<str:grade>/', views.record_books_subject_select, name='record_books_subject_select'),
    path('record-books/subject/<int:subject_id>/', views.record_books_week_select, name='record_books_week_select'),
    path('record-books/marksheet/<int:subject_id>/<int:week_id>/', views.coursework_marksheet, name='coursework_marksheet'),
    path('toggle-enroll/<int:student_id>/<int:subject_id>/', views.toggle_enrollment, name='toggle_enrollment'),
    path('exclude-class/', views.exclude_whole_class, name='exclude_whole_class'),

   ]
