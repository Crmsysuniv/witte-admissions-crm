from django.urls import path
from . import views

app_name = 'officer'

urlpatterns = [
    path('', views.workplace_view, name='workplace'),
    path('workplace/', views.workplace_view, name='workplace_alias'),
]
