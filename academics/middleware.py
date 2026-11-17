class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


import os
from django.shortcuts import render
from django.conf import settings

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # File ON = maintenance ON
        maintenance_file = os.path.join(settings.BASE_DIR, 'maintenance.on')
        is_maintenance = os.path.exists(maintenance_file)

        # Head / superuser can still enter, to test
        user = getattr(request, 'user', None)
        is_admin = bool(user and user.is_authenticated and user.is_superuser)

        # Let admin + login + static pass, block everyone else
        if is_maintenance and not is_admin:
            if not request.path.startswith('/static/') and not request.path.startswith('/admin/'):
                return render(request, 'kids/maintenance.html', status=503)

        return self.get_response(request)
