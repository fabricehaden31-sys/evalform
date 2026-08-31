class CalculateurSatisfaction:
    @staticmethod
    def calculer_score_global(evaluation):
        # Sécurité supplémentaire : on ne filtre que les questions de type échelle
        reponses_echelle = evaluation.reponses.filter(
            question__type_reponse='echelle_satisfaction',
            valeur_numerique__isnull=False
        )
        
        # Correction : on sauvegarde bien le 0 en base de données avant de le retourner
        if not reponses_echelle.exists():
            evaluation.score_global = 0.0
            evaluation.statut = "Non noté"
            evaluation.save()
            return 0.0
        
        total_obtenu = sum(r.valeur_numerique for r in reponses_echelle)
        total_max = reponses_echelle.count() * 5.0
        
        score_pourcentage = (total_obtenu / total_max) * 100
        
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