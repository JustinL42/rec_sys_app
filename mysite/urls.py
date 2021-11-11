"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.urls import include, path
from django.conf.urls import url

from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
	path('', include('recsys.urls'), name='home'),
    path('recsys/', include('recsys.urls')),
    
    url(r'^(accounts/)?signup/.*$', 
        views.SignUpView.as_view(), name='signup'),
    url(r'^(accounts/)?login/.*$', 
        auth_views.LoginView.as_view(), name='login'),
    url(r'^logout/$', auth_views.LogoutView.as_view(), name='logout'),

    url(r'^account/$', views.Account.as_view(), name='account'),
    
    url(r'^password_reset/$', 
        auth_views.PasswordResetView.as_view(), 
        name='password_reset'),
    url(r'^password_reset/done/$', 
        auth_views.PasswordResetDoneView.as_view(), 
        name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(), 
        name='password_reset_confirm'),
    url(r'^reset/done/$', 
        auth_views.PasswordResetCompleteView.as_view(), 
        name='password_reset_complete'),

    url(r'^password_change/$', auth_views.PasswordChangeView.as_view(
            template_name='registration/password_change.html'),
        name='password_change'),
    url(r'^password_change_done/$',
        auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done'),

    url(r'^username_change/$', 
        views.UserNameChangeView.as_view(), name='username_change'),
    url(r'^displayname_change/$', views.DisplayNameChangeView.as_view(),
        name='displayname_change'),
    url(r'^email_change/$', views.EmailChangeView.as_view(),
        name='email_change'),
    url(r'^account_delete/$', 
        views.AccountDeleteView.as_view(), name='account_delete'),
    path('admin/', admin.site.urls),
]
