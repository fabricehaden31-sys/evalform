from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Categorie, Evaluation, Formulaire, Question, Reponse, TypeQuestion


class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = ('id', 'nom')


class QuestionSerializer(serializers.ModelSerializer):
    # Rendu inscriptible (et optionnel) pour permettre la mise Ã  jour d'une
    # question existante sans la recrÃ©er â€” voir FormulaireSerializer.update().
    # Par dÃ©faut, DRF traite l'id comme read_only, ce qui empÃªchait tout
    # rapprochement avec les questions dÃ©jÃ  en base.
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Question
        fields = ('id', 'libelle', 'type_reponse', 'obligatoire', 'ordre', 'options')

    def validate_options(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Les options doivent Ãªtre une liste.')
        return value


class FormulaireSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)
    categorie_rel = CategorieSerializer(read_only=True)
    # Champ en Ã©criture pour associer une Categorie existante (par id) ;
    # categorie_rel ci-dessus reste en lecture seule pour l'affichage dÃ©taillÃ©.
    categorie_id = serializers.PrimaryKeyRelatedField(
        source='categorie_rel',
        queryset=Categorie.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    nombre_evaluations = serializers.IntegerField(source='evaluations.count', read_only=True)

    class Meta:
        model = Formulaire
        fields = (
            'id', 'titre', 'description', 'categorie', 'categorie_rel', 'categorie_id',
            'actif', 'date_creation', 'questions', 'nombre_evaluations',
        )
        read_only_fields = ('date_creation',)

    @transaction.atomic
    def create(self, validated_data):
        questions = validated_data.pop('questions', [])
        formulaire = Formulaire.objects.create(**validated_data)
        for index, question in enumerate(questions, start=1):
            question = dict(question)
            # Un id Ã©ventuellement fourni ne peut rÃ©fÃ©rencer une question
            # existante puisque le formulaire vient d'Ãªtre crÃ©Ã© : on l'ignore
            # pour Ã©viter toute collision de clÃ© primaire.
            question.pop('id', None)
            question.setdefault('ordre', index)
            Question.objects.create(formulaire=formulaire, **question)
        return formulaire

    @transaction.atomic
    def update(self, instance, validated_data):
        questions = validated_data.pop('questions', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if questions is not None:
            # Mise Ã  jour "upsert" : une question dont l'id correspond Ã  une
            # question existante du formulaire est mise Ã  jour en place (son
            # id est conservÃ©), une question sans id (ou avec un id inconnu)
            # est crÃ©Ã©e. Seules les questions absentes de la nouvelle liste
            # sont supprimÃ©es.
            # Cela Ã©vite de tout supprimer/recrÃ©er Ã  chaque modification, ce
            # qui aurait fait tomber en cascade (on_delete=CASCADE) toutes les
            # Reponse dÃ©jÃ  enregistrÃ©es pour les anciennes questions.
            questions_existantes = {q.id: q for q in instance.questions.all()}
            ids_conserves = set()

            for index, question_data in enumerate(questions, start=1):
                question_data = dict(question_data)
                question_id = question_data.pop('id', None)
                question_data.setdefault('ordre', index)

                if question_id and question_id in questions_existantes:
                    Question.objects.filter(pk=question_id).update(**question_data)
                    ids_conserves.add(question_id)
                else:
                    nouvelle_question = Question.objects.create(formulaire=instance, **question_data)
                    ids_conserves.add(nouvelle_question.id)

            instance.questions.exclude(id__in=ids_conserves).delete()

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
            raise serializers.ValidationError('Une question ne peut Ãªtre rÃ©pondue qu\u2019une seule fois.')
        unknown = set(submitted_ids) - set(questions)
        if unknown:
            raise serializers.ValidationError('Une rÃ©ponse cible une question inconnue.')
        missing = [q.id for q in questions.values() if q.obligatoire and q.id not in submitted_ids]
        if missing:
            raise serializers.ValidationError({'reponses': f'RÃ©ponses obligatoires manquantes : {missing}.'})
        for item in attrs['reponses']:
            question = questions[item['question_id']]
            numeric, text = item.get('valeur_numerique'), item.get('valeur_texte')
            if question.type_reponse == TypeQuestion.ECHELLE_SATISFACTION:
                if numeric is None:
                    raise serializers.ValidationError({'reponses': f'La question {question.id} attend une note de 1 Ã  5.'})
            else:
                if numeric is not None:
                    raise serializers.ValidationError({'reponses': f'La question {question.id} n\u2019attend pas de note numÃ©rique.'})
                if not text and question.obligatoire:
                    raise serializers.ValidationError({'reponses': f'La question {question.id} attend une rÃ©ponse texte.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        formulaire = self.context['formulaire']
        evaluation = Evaluation.objects.create(formulaire=formulaire)
        questions = {question.id: question for question in formulaire.questions.all()}
        for reponse in validated_data['reponses']:
            Reponse.objects.create(
                evaluation=evaluation,
                question=questions[reponse['question_id']],
                valeur_numerique=reponse.get('valeur_numerique'),
                valeur_texte=reponse.get('valeur_texte'),
            )
        evaluation.calculer_score_global()
        return evaluation


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = ('id', 'formulaire', 'date_soumission', 'score_global', 'statut')


class ReponseDetailSerializer(serializers.ModelSerializer):
    question_libelle = serializers.CharField(source='question.libelle', read_only=True)
    question_type = serializers.CharField(source='question.type_reponse', read_only=True)
    question_ordre = serializers.IntegerField(source='question.ordre', read_only=True)

    class Meta:
        model = Reponse
        fields = ('question', 'question_libelle', 'question_type', 'question_ordre', 'valeur_numerique', 'valeur_texte')


class EvaluationDetailSerializer(serializers.ModelSerializer):
    reponses = ReponseDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Evaluation
        fields = ('id', 'date_soumission', 'score_global', 'statut', 'reponses')


class ConnexionSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if user is None:
            raise serializers.ValidationError('Identifiants incorrects.')
        if not user.is_staff:
            raise serializers.ValidationError('Cet espace est rÃ©servÃ© aux administrateurs.')
        attrs['user'] = user
        return attrs
