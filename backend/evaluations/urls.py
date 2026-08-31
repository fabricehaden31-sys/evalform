from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConnexionView, DeconnexionView, FormulaireAdminViewSet, FormulairePublicDetailView, FormulairePublicListView, SoumettreEvaluationView, TableauDeBordView, UtilisateurActuelView

router = DefaultRouter()
router.register('administration/formulaires', FormulaireAdminViewSet, basename='formulaire-administration')

urlpatterns = [
    path('auth/connexion/', ConnexionView.as_view(), name='connexion'),
    path('auth/deconnexion/', DeconnexionView.as_view(), name='deconnexion'),
    path('auth/moi/', UtilisateurActuelView.as_view(), name='utilisateur-actuel'),
    path('formulaires/', FormulairePublicListView.as_view(), name='formulaire-list'),
    path('formulaires/<int:pk>/', FormulairePublicDetailView.as_view(), name='formulaire-detail'),
    path('formulaires/<int:pk>/evaluations/', SoumettreEvaluationView.as_view(), name='evaluation-soumettre'),
    path('administration/tableau-de-bord/', TableauDeBordView.as_view(), name='tableau-de-bord'),
    path('', include(router.urls)),
]
