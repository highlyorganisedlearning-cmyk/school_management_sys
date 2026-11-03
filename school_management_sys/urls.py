from django.contrib import admin
from django.urls import path, include
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('kids.urls')),
    path('accounts/', include('django.contrib.auth.urls')),  # this gives you /accounts/login/
    path('academics/', include('academics.urls')),
]