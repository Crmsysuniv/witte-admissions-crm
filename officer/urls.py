from django.urls import path
from student import views as student_views
from . import views

app_name = 'officer'

urlpatterns = [
    path('', views.workplace_view, name='workplace'),
    path('workplace/', views.workplace_view, name='workplace_alias'),
    path('applications/', views.applications_list_view, name='applications_list'),
    path('applications/<int:pk>/', views.application_detail_view, name='application_detail'),
    path('inquiries/', views.inquiries_view, name='inquiries'),
    path('protocols/', views.protocols_view, name='protocols'),
    path('rating/', student_views.rating_view, name='rating'),
    path('export/rating/', views.export_rating_xlsx_view, name='export_rating_xlsx'),
    path('applications/<int:pk>/receipt/docx/', views.download_receipt_docx_view, name='application_receipt_docx'),
]
