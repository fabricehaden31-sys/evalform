from django.contrib import admin
from .models import Categorie, Evaluation, Formulaire, Question, Reponse


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


@admin.register(Formulaire)
class FormulaireAdmin(admin.ModelAdmin):
    list_display = ('titre', 'categorie', 'actif', 'date_creation')
    list_filter = ('actif', 'categorie')
    inlines = [QuestionInline]


admin.site.register([Categorie, Evaluation, Reponse])
