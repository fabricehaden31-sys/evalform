from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Categorie, Evaluation, Formulaire, Question, Reponse


class EvaluationApiTests(APITestCase):
    def setUp(self):
        self.formulaire = Formulaire.objects.create(titre='Ã‰valuation de formation')
        self.question_note = Question.objects.create(
            formulaire=self.formulaire,
            libelle='La formation Ã©tait utile.',
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
                {'question_id': self.question_commentaire.id, 'valeur_texte': 'TrÃ¨s bonne formation.'},
            ]},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['score_global'], 80.0)
        self.assertEqual(response.data['statut'], 'Excellent')

    def test_le_tableau_de_bord_est_reserve_a_l_administrateur(self):
        self.assertEqual(self.client.get('/api/administration/tableau-de-bord/').status_code, 403)
        admin = User.objects.create_user('admin', password='mot-de-passe', is_staff=True)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get('/api/administration/tableau-de-bord/').status_code, 200)

    def test_connexion_administrateur(self):
        User.objects.create_user('admin', password='mot-de-passe', is_staff=True)
        response = self.client.post('/api/auth/connexion/', {'username': 'admin', 'password': 'mot-de-passe'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_administrateur'])


class ModificationFormulaireTests(APITestCase):
    """Non-rÃ©gression pour le bug de suppression en cascade des rÃ©ponses."""

    def setUp(self):
        self.admin = User.objects.create_user('admin', password='mot-de-passe', is_staff=True)
        self.formulaire = Formulaire.objects.create(titre='Satisfaction module Django')
        self.q1 = Question.objects.create(formulaire=self.formulaire, libelle='Q1', ordre=1)
        self.q2 = Question.objects.create(
            formulaire=self.formulaire, libelle='Q2',
            type_reponse='commentaire_libre', obligatoire=False, ordre=2,
        )
        self.evaluation = Evaluation.objects.create(formulaire=self.formulaire)
        self.reponse = Reponse.objects.create(evaluation=self.evaluation, question=self.q1, valeur_numerique=5)

    def test_ajouter_une_question_ne_supprime_pas_les_reponses_existantes(self):
        self.client.force_authenticate(self.admin)
        payload = {
            'questions': [
                {'id': self.q1.id, 'libelle': self.q1.libelle, 'ordre': 1},
                {'id': self.q2.id, 'libelle': self.q2.libelle, 'type_reponse': 'commentaire_libre', 'obligatoire': False, 'ordre': 2},
                {'libelle': 'Nouvelle question ajoutÃ©e', 'ordre': 3},
            ],
        }
        response = self.client.patch(f'/api/administration/formulaires/{self.formulaire.id}/', payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Question.objects.filter(id=self.q1.id).exists())
        self.assertTrue(Question.objects.filter(id=self.q2.id).exists())
        # La rÃ©ponse historique n'a pas Ã©tÃ© supprimÃ©e en cascade
        self.assertTrue(Reponse.objects.filter(id=self.reponse.id).exists())
        self.assertEqual(self.formulaire.questions.count(), 3)

    def test_retirer_une_question_de_la_liste_la_supprime(self):
        self.client.force_authenticate(self.admin)
        payload = {'questions': [{'id': self.q1.id, 'libelle': self.q1.libelle, 'ordre': 1}]}
        response = self.client.patch(f'/api/administration/formulaires/{self.formulaire.id}/', payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Question.objects.filter(id=self.q1.id).exists())
        self.assertFalse(Question.objects.filter(id=self.q2.id).exists())


class CalculScoreTests(APITestCase):
    """Non-rÃ©gression pour l'incohÃ©rence de calculer_score_global sans rÃ©ponse Ã  Ã©chelle."""

    def setUp(self):
        self.formulaire = Formulaire.objects.create(titre='Feedback libre')
        self.question_libre = Question.objects.create(
            formulaire=self.formulaire, libelle='Vos remarques ?',
            type_reponse='commentaire_libre', obligatoire=True, ordre=1,
        )

    def test_evaluation_sans_question_a_echelle_est_marquee_non_evaluee(self):
        response = self.client.post(
            f'/api/formulaires/{self.formulaire.id}/evaluations/',
            {'reponses': [{'question_id': self.question_libre.id, 'valeur_texte': 'Rien Ã  signaler.'}]},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data['score_global'])
        self.assertEqual(response.data['statut'], 'Non Ã©valuÃ©')

    def test_une_valeur_numerique_sur_une_question_texte_est_rejetee(self):
        response = self.client.post(
            f'/api/formulaires/{self.formulaire.id}/evaluations/',
            {'reponses': [{'question_id': self.question_libre.id, 'valeur_numerique': 5}]},
            format='json',
        )
        self.assertEqual(response.status_code, 400)


class CategorieAssociationTests(APITestCase):
    """Non-rÃ©gression pour l'impossibilitÃ© d'associer une Categorie via l'API."""

    def setUp(self):
        self.admin = User.objects.create_user('admin', password='mot-de-passe', is_staff=True)
        self.categorie = Categorie.objects.create(nom='SÃ©curitÃ©')
        self.formulaire = Formulaire.objects.create(titre='Audit sÃ©curitÃ©')

    def test_associer_une_categorie_existante_via_categorie_id(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f'/api/administration/formulaires/{self.formulaire.id}/',
            {'categorie_id': self.categorie.id},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.formulaire.refresh_from_db()
        self.assertEqual(self.formulaire.categorie_rel_id, self.categorie.id)
        self.assertEqual(response.data['categorie_rel']['nom'], 'SÃ©curitÃ©')
