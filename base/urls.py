from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import handler404

handler404 = views.custom_404
urlpatterns = [
    path('', views.index, name='initial'),
    path('admin/', admin.site.urls),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/change_password/', views.change_password, name='change_password'),
    path('profile/delete/', views.delete_account, name='delete_account'),

    # ==================== СТУДЕНЧЕСКИЕ МАРШРУТЫ ====================
    path('student/profile/', views.profile, name='profile'),
    path('student/result/<int:pk>/', views.result_detail, name='result_detail'),
    path('student/test/<str:test_kind>/', views.test_view, name='test_view'),
    path('student/labs/lab/<int:lab_id>/', views.lab_view, name='lab'),
    path('student/labs/', views.student_labs, name='student_labs'),
    path('student/lab/<int:lab_id>/submit/', views.submit_lab, name='submit_lab'),
    path('student/teacher-tests/', views.student_teacher_tests, name='student_teacher_tests'),
    path('student/teacher-tests/<int:test_id>/', views.take_teacher_test, name='take_teacher_test'),

    # Чаты студентов с одногруппниками
    path('student/groupmates/', views.groupmates_list, name='groupmates_list'),
    path('student/chat/<int:user_id>/', views.chat_detail, name='chat_detail'),
    path('student/chat/send/', views.send_message, name='send_message'),
    path('student/chat/unread-count/', views.get_unread_messages_count, name='get_unread_messages_count'),
    path('student/chat/users-list/', views.get_chat_users_list, name='get_chat_users_list'),
    path('student/chat/get-messages/<int:user_id>/', views.get_chat_messages, name='get_chat_messages'),

    # Чат студента с учителем
    path('student/chat/teacher/list/', views.student_teacher_chat_list, name='student_teacher_chat_list'),
    path('student/chat_with_teacher/', views.student_teacher_chat_list, name='student_chat_with_teacher'),
    path('student/chat/teacher/detail/<int:user_id>/', views.teacher_student_chat_detail,
         name='student_teacher_chat_detail'),
    path('student/chat/teacher/detail/<int:user_id>/', views.teacher_student_chat_detail, name='student_teacher_chat_detail'),
    path('teacher/chat/student/detail/<int:user_id>/', views.teacher_student_chat_detail, name='teacher_student_chat_detail'),
    # ==================== УЧИТЕЛЬСКИЕ МАРШРУТЫ ====================
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/students/', views.teacher_students_list, name='teacher_students_list'),
    path('teacher/students/student/<int:student_id>/', views.teacher_student_stats, name='teacher_student_stats'),
    path('teacher/student_results/', views.student_results, name='student_results'),
    path('teacher/result/<int:pk>/', views.result_detail, name='teacher_result_detail'),
    path('teacher/report/download/', views.download_report, name='download_report'),
    path('teacher/grade-test/<int:result_id>/', views.grade_test_result, name='grade_test'),
    path('teacher/student_results/export/', views.export_student_results_excel, name='export_student_results'),

    # Чаты учителя с учениками
    path('teacher/chat/students/list/', views.teacher_student_chat_list, name='teacher_student_chat_list'),
    path('teacher/chat/student/detail/<int:user_id>/', views.teacher_student_chat_detail,
         name='teacher_student_chat_detail'),

    # API для чатов (общие, без префикса роли, т.к. используются AJAX)
    path('chat/teacher-student/send/', views.send_teacher_student_message, name='send_teacher_student_message'),
    path('chat/teacher-student/get-messages/<int:user_id>/', views.get_teacher_student_messages,
         name='get_teacher_student_messages'),

    # Лабораторные работы (учитель)
    path('teacher/labs/', views.teacher_labs, name='teacher_labs'),
    path('teacher/labs/lab/<int:lab_id>/', views.lab_detail, name='lab_detail'),
    path('teacher/labs/lab/new/', views.create_lab_work, name='create_lab'),
    path('teacher/lab/delete/<int:lab_id>/', views.delete_lab_work, name='delete_lab_work'),
    path('teacher/lab/submission/<int:submission_id>/', views.submission_detail, name='submission_detail'),
    path('teacher/lab/submission/<int:submission_id>/download/', views.serve_submission_file,
         name='serve_submission_file'),
    path('teacher/student_lab/<int:lab_id>/', views.teacher_lab_detail, name='teacher_lab_detail'),

    # Вопросы и тесты (учитель)
    path('teacher/questions/', views.manage_questions, name='manage_questions'),
    path('teacher/questions/add/', views.add_question, name='add_question'),
    path('teacher/tests/', views.teacher_manage_tests, name='teacher_manage_tests'),
    path('teacher/tests/create/', views.create_teacher_test, name='create_teacher_test'),
    path('teacher/tests/<int:test_id>/', views.teacher_test_detail, name='teacher_test_detail'),
    path('teacher/tests/delete/<int:test_id>/', views.delete_teacher_test, name='delete_teacher_test'),
    path('teacher/tests/<int:test_id>/assign/', views.edit_test_assignment, name='edit_test_assignment'),

    # ==================== УВЕДОМЛЕНИЯ (ОБЩИЕ) ====================
    path('notifications/get/', views.get_notifications, name='get_notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/unread-count/', views.get_unread_notifications_count, name='unread_notifications_count'),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('notifications/delete-all/', views.delete_all_notifications, name='delete_all_notifications'),

# Добавьте эти пути в конец urlpatterns:

# API для файлов и голосовых сообщений
    path('chat/teacher-student/send-file/', views.send_teacher_student_file, name='send_teacher_student_file'),
    path('chat/teacher-student/send-voice/', views.send_teacher_student_voice, name='send_teacher_student_voice'),
    path('chat/teacher-student/add-reaction/', views.add_message_reaction, name='add_message_reaction'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)