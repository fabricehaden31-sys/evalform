from pathlib import Path

from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path

from evalform_project.settings import BASE_DIR

FRONTEND_DIR = (BASE_DIR.parent / 'frontend').resolve()


def servir_frontend(request, page='index.html'):
    relative = page.strip('/') or 'index.html'
    target = (FRONTEND_DIR / relative).resolve()
    if not str(target).startswith(str(FRONTEND_DIR)) or not target.is_file():
        raise Http404()
    return FileResponse(open(target, 'rb'))


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('evaluations.urls')),
    path('', servir_frontend),
    path('<path:page>', servir_frontend),
]
