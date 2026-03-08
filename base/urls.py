from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='initial'),
    path('start/', views.start, name='start'),
    path('finish/', views.finish, name='finish'),
    path('register/', views.register,  name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
]
