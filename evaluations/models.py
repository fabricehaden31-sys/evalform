from django.db import models

class TypeQuestion(models.TextChoices):
    ECHELLE_SATISFACTION = 'echelle_satisfaction', 'Ã‰chelle de satisfaction'
    COMMENTAIRE_LIBRE = 'commentaire_libre', 'Commentaire libre'
    CHOIX_MULTIPLE = 'choix_multiple', 'Choix multiple'

class Categorie(models.Model):
    nom = models.CharField(max_length=100)

    def __str__(self):
        return self.nom

class Formulaire(models.Model):
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    categorie_rel = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, blank=True, related_name='formulaires')
    categorie = models.CharField(max_length=100, blank=True, null=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre

class Question(models.Model):
    formulaire = models.ForeignKey(Formulaire, on_delete=models.CASCADE, related_name='questions')
    libelle = models.TextField()
    type_reponse = models.CharField(max_length=50, choices=TypeQuestion.choices, default=TypeQuestion.ECHELLE_SATISFACTION)
    obligatoire = models.BooleanField(default=True)
    ordre = models.IntegerField(default=1)
    options = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f"{self.ordre}. {self.libelle}"

class Evaluation(models.Model):
    formulaire = models.ForeignKey(Formulaire, on_delete=models.CASCADE, related_name='evaluations')
    date_soumission = models.DateTimeField(auto_now_add=True)
    score_global = models.FloatField(null=True, blank=True)
    statut = models.CharField(max_length=50, blank=True, null=True)

    def calculer_score_global(self):
        """DÃ©lÃ¨gue au service de calcul (import diffÃ©rÃ© pour Ã©viter un import circulaire)."""
        from .services import CalculateurSatisfaction
        return CalculateurSatisfaction.calculer_score_global(self.formulaire, self)

    def __str__(self):
        return f"Ã‰valuation #{self.id} - {self.formulaire.titre}"

class Reponse(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='reponses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    valeur_numerique = models.FloatField(null=True, blank=True)  # Stocke 1, 2, 3, 4 ou 5
    valeur_texte = models.TextField(null=True, blank=True)       # Stocke le libellÃ© ou le commentaire libre

    def __str__(self):
        return f"RÃ©ponse Ã  Q{self.question.id}"
