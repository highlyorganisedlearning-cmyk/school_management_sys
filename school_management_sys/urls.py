from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from kids.views import main_menu

urlpatterns = [
    path('', main_menu, name='main_menu'),
    path('admin/', admin.site.urls),
    path('', include('kids.urls')),
    path('accounts/', include('django.contrib.auth.urls')),  # this gives you /accounts/login/
    path('academics/', include('academics.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='kids/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]