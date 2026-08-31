from django.db.models import Avg, Count, Q
from django.contrib.auth import login, logout
from rest_framework import generics, permissions, response, status, views, viewsets
from rest_framework.authtoken.models import Token

from .models import Formulaire
from .serializers import ConnexionSerializer, EvaluationSerializer, EvaluationSoumissionSerializer, FormulaireSerializer

class IsAdministrator(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)

class ConnexionView(views.APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ConnexionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        token, _created = Token.objects.get_or_create(user=user)
        return response.Response({
            'username': user.get_username(),
            'is_administrateur': user.is_staff,
            'token': token.key,
        })

class DeconnexionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

class UtilisateurActuelView(views.APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return response.Response({'authentifie': False, 'is_administrateur': False})
        return response.Response({
            'authentifie': True,
            'username': request.user.get_username(),
            'is_administrateur': request.user.is_staff,
        })

class FormulairePublicListView(generics.ListAPIView):
    serializer_class = FormulaireSerializer
    queryset = Formulaire.objects.filter(actif=True).prefetch_related('questions')

class FormulairePublicDetailView(generics.RetrieveAPIView):
    serializer_class = FormulaireSerializer
    queryset = Formulaire.objects.filter(actif=True).prefetch_related('questions')

class SoumettreEvaluationView(views.APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        formulaire = generics.get_object_or_404(Formulaire.objects.prefetch_related('questions'), pk=pk, actif=True)
        serializer = EvaluationSoumissionSerializer(data=request.data, context={'formulaire': formulaire})
        serializer.is_valid(raise_exception=True)
        evaluation = serializer.save()
        return response.Response(EvaluationSerializer(evaluation).data, status=201)

class FormulaireAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdministrator]
    serializer_class = FormulaireSerializer
    queryset = Formulaire.objects.all().prefetch_related('questions')

class TableauDeBordView(views.APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        resultats = Formulaire.objects.aggregate(
            nombre_evaluations=Count('evaluations'),
            satisfaction_moyenne=Avg('evaluations__score_global'),
            formulaires_actifs=Count('id', filter=Q(actif=True)),
        )
        return response.Response(resultats)