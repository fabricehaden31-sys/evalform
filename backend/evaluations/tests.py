from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Formulaire, Question


class EvaluationApiTests(APITestCase):
    def setUp(self):
        self.formulaire = Formulaire.objects.create(titre='Évaluation de formation')
        self.question_note = Question.objects.create(
            formulaire=self.formulaire,
            libelle='La formation était utile.',
            ordre=1,
        )
        self.question_commentaire = Question.objects.create(
            formulaire=self.formulaire,
            libelle='Un commentaire ?',
            type_reponse='commentaire_libre',
            obligatoire=False,
            ordre=2,
        )

    def test_un_apprenant_peut_soumettre_une_evaluation(self):
        response = self.client.post(
            f'/api/formulaires/{self.formulaire.id}/evaluations/',
            {'reponses': [
                {'question_id': self.question_note.id, 'valeur_numerique': 4},
                {'question_id': self.question_commentaire.id, 'valeur_texte': 'Très bonne formation.'},
            ]},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['score_global'], 80.0)
        self.assertEqual(response.data['statut'], 'Excellent')

    def test_le_tableau_de_bord_est_reserve_a_l_administrateur(self):
        self.assertEqual(self.client.get('/api/administration/tableau-de-bord/').status_code, 401)
        admin = User.objects.create_user('admin', password='mot-de-passe', is_staff=True)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get('/api/administration/tableau-de-bord/').status_code, 200)

    def test_connexion_administrateur(self):
        User.objects.create_user('admin', password='mot-de-passe', is_staff=True)
        response = self.client.post('/api/auth/connexion/', {'username': 'admin', 'password': 'mot-de-passe'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_administrateur'])
        self.assertTrue(response.data['token'])

    def test_un_administrateur_peut_creer_un_formulaire(self):
        admin = User.objects.create_user('admin', password='mot-de-passe', is_staff=True)
        self.client.force_authenticate(admin)
        response = self.client.post('/api/administration/formulaires/', {
            'titre': 'ISO 27001',
            'lieu': 'Lomé',
            'formateurs': 'Paul-Hermann Alao, Marie K.',
            'categorie': 'Sécurité',
            'questions': [
                {'libelle': 'Le contenu était clair.', 'type_reponse': 'echelle_satisfaction', 'obligatoire': True},
            ],
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['lieu'], 'Lomé')
        self.assertEqual(len(response.data['questions']), 1)
