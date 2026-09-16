"""
URL configuration for witte_crm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views
from admissions import views as admissions_views
from accounts import views as accounts_views

urlpatterns = [
    path('', core_views.home, name='home'),
    path('login/', accounts_views.login_view, name='login'),
    path('logout/', accounts_views.logout_view, name='logout'),
    path('register/', accounts_views.register_view, name='register'),
    path('accounts/', include('accounts.urls')),
    path('faculties/', admissions_views.faculties_list, name='faculties_list'),
    path('programs/', admissions_views.programs_catalog, name='programs_catalog'),
    path('rules/', admissions_views.admissions_rules, name='admissions_rules'),
    path('calculator/', admissions_views.score_calculator, name='score_calculator'),
    path('tuition/', admissions_views.tuition_fees, name='tuition_fees'),
    path('dormitory/', admissions_views.dormitory_info, name='dormitory_info'),
    path('faq/', core_views.faq, name='faq'),
    path('contacts/', core_views.contacts, name='contacts'),
    path('feedback/', include('feedback.urls')),
    path('admissions/', include('admissions.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

