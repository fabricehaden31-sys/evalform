from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Categorie, Evaluation, Formulaire, Question, Reponse, TypeQuestion
from .services import CalculateurSatisfaction

class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = ('id', 'nom')

class QuestionSerializer(serializers.ModelSerializer):
    # Ajout de l'ID non requis pour permettre la mise à jour ciblée d'une question
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Question
        fields = ('id', 'libelle', 'type_reponse', 'obligatoire', 'ordre', 'options')

    def validate_options(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Les options doivent être une liste.')
        return value

class FormulaireSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)
    categorie_rel = CategorieSerializer(read_only=True)
    # Permet de lier une catégorie via l'API en envoyant son ID
    categorie_id = serializers.PrimaryKeyRelatedField(
        queryset=Categorie.objects.all(), source='categorie_rel', write_only=True, required=False, allow_null=True
    )
    nombre_evaluations = serializers.IntegerField(source='evaluations.count', read_only=True)

    class Meta:
        model = Formulaire
        fields = ('id', 'titre', 'description', 'lieu', 'formateurs', 'categorie', 'categorie_rel', 'categorie_id', 'actif', 'date_creation', 'questions', 'nombre_evaluations')
        read_only_fields = ('date_creation',)

    @transaction.atomic
    def create(self, validated_data):
        questions = validated_data.pop('questions', [])
        formulaire = Formulaire.objects.create(**validated_data)
        for index, question in enumerate(questions, start=1):
            question.setdefault('ordre', index)
            # Retirer l'id s'il a été fourni par erreur lors de la création
            question.pop('id', None) 
            Question.objects.create(formulaire=formulaire, **question)
        return formulaire

    @transaction.atomic
    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions', None)
        
        # Mise à jour des champs de base du formulaire
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        # Mise à jour intelligente des questions (évite le delete en cascade)
        if questions_data is not None:
            existing_questions = {q.id: q for q in instance.questions.all()}
            updated_ids = []

            for index, q_data in enumerate(questions_data, start=1):
                q_id = q_data.get('id')
                q_data['ordre'] = index

                if q_id and q_id in existing_questions:
                    # Mise à jour de la question existante
                    q_instance = existing_questions[q_id]
                    for attr, val in q_data.items():
                        setattr(q_instance, attr, val)
                    q_instance.save()
                    updated_ids.append(q_instance.id)
                else:
                    # Création d'une nouvelle question ajoutée au formulaire
                    q_data.pop('id', None)
                    new_q = Question.objects.create(formulaire=instance, **q_data)
                    updated_ids.append(new_q.id)

            # Suppression uniquement des questions qui ont été retirées du formulaire
            for q_id, q_instance in existing_questions.items():
                if q_id not in updated_ids:
                    q_instance.delete()

        return instance

class ReponseSoumissionSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    valeur_numerique = serializers.FloatField(required=False, allow_null=True, min_value=1, max_value=5)
    valeur_texte = serializers.CharField(required=False, allow_blank=True, allow_null=True)

class EvaluationSoumissionSerializer(serializers.Serializer):
    reponses = ReponseSoumissionSerializer(many=True)

    def validate(self, attrs):
        formulaire = self.context['formulaire']
        questions = {question.id: question for question in formulaire.questions.all()}
        submitted_ids = [item['question_id'] for item in attrs['reponses']]
        
        if len(submitted_ids) != len(set(submitted_ids)):
            raise serializers.ValidationError('Une question ne peut être répondue qu’une seule fois.')
        
        unknown = set(submitted_ids) - set(questions)
        if unknown:
            raise serializers.ValidationError('Une réponse cible une question inconnue.')
        
        missing = [q.id for q in questions.values() if q.obligatoire and q.id not in submitted_ids]
        if missing:
            raise serializers.ValidationError({'reponses': f'Réponses obligatoires manquantes : {missing}.'})
        
        for item in attrs['reponses']:
            question = questions[item['question_id']]
            numeric, text = item.get('valeur_numerique'), item.get('valeur_texte')
            
            if question.type_reponse == TypeQuestion.ECHELLE_SATISFACTION and numeric is None:
                raise serializers.ValidationError({'reponses': f'La question {question.id} attend une note de 1 à 5.'})
            
            # SÉCURITÉ : Forcer la valeur numérique à None si ce n'est pas une question de type échelle
            if question.type_reponse != TypeQuestion.ECHELLE_SATISFACTION:
                item['valeur_numerique'] = None
                if not text and question.obligatoire:
                    raise serializers.ValidationError({'reponses': f'La question {question.id} attend une réponse texte.'})
                    
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        formulaire = self.context['formulaire']
        evaluation = Evaluation.objects.create(formulaire=formulaire)
        questions = {question.id: question for question in formulaire.questions.all()}
        for response in validated_data['reponses']:
            Reponse.objects.create(
                evaluation=evaluation,
                question=questions[response['question_id']],
                valeur_numerique=response.get('valeur_numerique'),
                valeur_texte=response.get('valeur_texte'),
            )
        CalculateurSatisfaction.calculer_score_global(evaluation)
        return evaluation

class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = ('id', 'formulaire', 'date_soumission', 'score_global', 'statut')

class ConnexionSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if user is None:
            raise serializers.ValidationError('Identifiants incorrects.')
        if not user.is_staff:
            raise serializers.ValidationError('Cet espace est réservé aux administrateurs.')
        attrs['user'] = user
        return attrs