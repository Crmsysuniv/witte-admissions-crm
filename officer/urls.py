from django.urls import path
from . import views

app_name = 'officer'

urlpatterns = [
    path('', views.workplace_view, name='workplace'),
    path('workplace/', views.workplace_view, name='workplace_alias'),
    path('applications/', views.applications_list_view, name='applications_list'),
    path('applications/<int:pk>/', views.application_detail_view, name='application_detail'),
    path('inquiries/', views.inquiries_view, name='inquiries'),
]
