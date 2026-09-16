from django.urls import path
from core import views as core_views
from . import views

app_name = 'admissions'

urlpatterns = [
    path('faculties/', views.faculties_list, name='faculties_list'),
    path('programs/', views.programs_catalog, name='programs_catalog'),
    path('specialties/<int:pk>/', views.specialty_detail, name='specialty_detail'),
    path('rules/', views.admissions_rules, name='admissions_rules'),
    path('calculator/', views.score_calculator, name='score_calculator'),
    path('tuition/', views.tuition_fees, name='tuition_fees'),
    path('dormitory/', views.dormitory_info, name='dormitory_info'),
    path('faq/', core_views.faq, name='faq'),
    path('contacts/', core_views.contacts, name='contacts'),
]
