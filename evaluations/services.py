from .models import TypeQuestion


class CalculateurSatisfaction:
    """Calcule le score de satisfaction global d'une Ã©valuation.

    Seules les rÃ©ponses aux questions de type Â« Ã©chelle de satisfaction Â»
    appartenant au formulaire concernÃ© sont prises en compte : cela Ã©vite
    qu'une valeur numÃ©rique fournie par erreur (ou de faÃ§on malveillante)
    sur une question de type commentaire libre / choix multiple ne fausse
    le score.
    """

    @staticmethod
    def calculer_score_global(formulaire, evaluation):
        questions_echelle_ids = formulaire.questions.filter(
            type_reponse=TypeQuestion.ECHELLE_SATISFACTION
        ).values_list('id', flat=True)

        reponses_echelle = evaluation.reponses.filter(
            question_id__in=questions_echelle_ids,
            valeur_numerique__isnull=False,
        )

        if not reponses_echelle.exists():
            # Aucune question Ã  Ã©chelle n'a Ã©tÃ© notÃ©e : on ne peut pas
            # calculer de score. On Ã©vite de renvoyer 0.0 (qui laisserait
            # croire Ã  un score de 0 % / statut "Critique") tout en gardant
            # les champs enregistrÃ©s cohÃ©rents avec la valeur retournÃ©e.
            evaluation.score_global = None
            evaluation.statut = "Non Ã©valuÃ©"
            evaluation.save()
            return evaluation.score_global

        total_obtenu = sum(r.valeur_numerique for r in reponses_echelle)
        total_max = reponses_echelle.count() * 5.0

        score_pourcentage = (total_obtenu / total_max) * 100

        # Attribution du statut selon le score calculÃ©
        if score_pourcentage >= 80:
            statut = "Excellent"
        elif score_pourcentage >= 60:
            statut = "Satisfaisant"
        elif score_pourcentage >= 40:
            statut = "Insuffisant"
        else:
            statut = "Critique"

        evaluation.score_global = round(score_pourcentage, 2)
        evaluation.statut = statut
        evaluation.save()

        return evaluation.score_global
