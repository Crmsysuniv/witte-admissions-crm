from django.urls import path
from . import views

app_name = 'student'

urlpatterns = [
    path('', views.dashboard_view, name='index'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
]
