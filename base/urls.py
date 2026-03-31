from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='initial'),
    # path('start/', views.start, name='start'),
    # path('finish/', views.finish, name='finish'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('result/<int:pk>/', views.result_detail, name='result_detail'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/password/', views.change_password, name='change_password'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('test/<str:test_kind>/', views.test_view, name='test_view'),

    # Учительские маршруты
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/student_results', views.student_results, name='student_results'),
    path('teacher/manage-tests/', views.manage_tests, name='manage_tests'),
]
