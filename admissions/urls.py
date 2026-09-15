from django.urls import path
from . import views

app_name = 'admissions'

urlpatterns = [
    path('faculties/', views.faculties_list, name='faculties_list'),
    path('programs/', views.programs_catalog, name='programs_catalog'),
    path('specialties/<int:pk>/', views.specialty_detail, name='specialty_detail'),
]
