from django.contrib.auth import login, logout
from django.db.models import Avg, Count, Q
from rest_framework import generics, permissions, response, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from .models import Formulaire
from .serializers import ConnexionSerializer, EvaluationDetailSerializer, EvaluationSerializer, EvaluationSoumissionSerializer, FormulaireSerializer


class IsAdministrator(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class ConnexionView(views.APIView):
    def post(self, request):
        serializer = ConnexionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return response.Response({
            'username': user.get_username(),
            'is_administrateur': user.is_staff,
        })


class DeconnexionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
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
    def post(self, request, pk):
        formulaire = generics.get_object_or_404(Formulaire.objects.prefetch_related('questions'), pk=pk, actif=True)
        serializer = EvaluationSoumissionSerializer(data=request.data, context={'formulaire': formulaire})
        serializer.is_valid(raise_exception=True)
        evaluation = serializer.save()
        return response.Response(EvaluationSerializer(evaluation).data, status=201)


class ReponsesPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50


class FormulaireAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdministrator]
    serializer_class = FormulaireSerializer
    queryset = Formulaire.objects.all().prefetch_related('questions')

    @action(detail=True, methods=['get'], url_path='reponses')
    def reponses(self, request, pk=None):
        formulaire = self.get_object()
        evaluations = (
            formulaire.evaluations
            .prefetch_related('reponses__question')
            .order_by('-date_soumission')
        )
        paginator = ReponsesPagination()
        page = paginator.paginate_queryset(evaluations, request)
        serializer = EvaluationDetailSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class TableauDeBordView(views.APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        resultats = Formulaire.objects.aggregate(
            nombre_evaluations=Count('evaluations'),
            satisfaction_moyenne=Avg('evaluations__score_global'),
            formulaires_actifs=Count('id', filter=Q(actif=True)),
        )
        return response.Response(resultats)
