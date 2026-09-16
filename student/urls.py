from django.urls import path
from . import views

app_name = 'student'

urlpatterns = [
    path('', views.dashboard_view, name='index'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('apply/', views.apply_view, name='apply'),
    path('documents/', views.documents_view, name='documents'),
    path('rating/', views.rating_view, name='rating'),
    path('rating/export/', views.export_rating_xlsx_view, name='rating_export_xlsx'),
    path('applications/<int:application_id>/withdraw/', views.withdraw_application_view, name='withdraw_application'),
    path('applications/<int:application_id>/receipt/docx/', views.download_receipt_docx_view, name='download_receipt_docx'),
]
