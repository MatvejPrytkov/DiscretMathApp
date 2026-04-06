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
    path('teacher/manage-tests/', views.manage_tests, name='manage_tests'),
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
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)