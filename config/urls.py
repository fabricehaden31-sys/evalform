from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('evaluations.urls')),
    # Frontend statique (pages HTML + css/ + js/)
    path('', serve, {'path': 'index.html', 'document_root': settings.FRONTEND_DIR}),
    re_path(r'^(?P<path>.*)$', serve, {'document_root': settings.FRONTEND_DIR}),
]
