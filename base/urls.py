from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
urlpatterns = [
    path('', views.index, name='initial'),
    path('admin/', admin.site.urls),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('result/<int:pk>/', views.result_detail, name='result_detail'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/password/', views.change_password, name='change_password'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('test/<str:test_kind>/', views.test_view, name='test_view'),
    path("teacher/report/download/", views.download_report, name="download_report"),
    # Учительские маршруты
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/student_results', views.student_results, name='student_results'),
    # 🆕 МАРШРУТЫ ДЛЯ ОЦЕНОК
    path('teacher/grade-test/<int:result_id>/', views.grade_test_result, name='grade_test'),

    # 🆕 МАРШРУТЫ ДЛЯ ЛАБОРАТОРНЫХ
    path('lab/<int:lab_id>/', views.lab_view, name='lab'),
    path('teacher/labs/', views.teacher_labs, name='teacher_labs'),
    path('teacher/lab/<int:lab_id>/', views.lab_detail, name='lab_detail'),
    path('teacher/lab/new/', views.create_lab_work, name='create_lab'),
    path('student/labs/', views.student_labs, name='student_labs'),
    path('student/lab/<int:lab_id>/submit/', views.submit_lab, name='submit_lab'),

    path('lab/<int:lab_id>/submit/', views.submit_lab, name='submit_lab'),
    path('lab/delete/<int:lab_id>/', views.delete_lab_work, name='delete_lab_work'),
    path('teacher/questions/', views.manage_questions, name='manage_questions'),
    path('teacher/questions/add/', views.add_question, name='add_question'),
    path('teacher/tests/', views.teacher_manage_tests, name='teacher_manage_tests'),
    path('teacher/tests/create/', views.create_teacher_test, name='create_teacher_test'),
    path('teacher/tests/<int:test_id>/', views.teacher_test_detail, name='teacher_test_detail'),
    path('student/teacher-tests/', views.student_teacher_tests, name='student_teacher_tests'),
    path('student/teacher-test/<int:test_id>/', views.take_teacher_test, name='take_teacher_test'),
    path('teacher/student_lab/<int:lab_id>/', views.teacher_lab_detail, name='teacher_lab_detail'),
    path('teacher/tests/delete/<int:test_id>/', views.delete_teacher_test, name='delete_teacher_test'),
    path('teacher/lab/submission/<int:submission_id>/', views.submission_detail, name='submission_detail'),
    path('teacher/student_results/export/', views.export_student_results_excel, name='export_student_results'),
    path('notifications/get/', views.get_notifications, name='get_notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/unread-count/', views.get_unread_notifications_count, name='unread_notifications_count'),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('notifications/delete-all/', views.delete_all_notifications, name='delete_all_notifications'),
    path('teacher/lab/submission/<int:submission_id>/download/', views.serve_submission_file, name='serve_submission_file'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)