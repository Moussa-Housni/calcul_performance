from django.contrib import admin

from .models import Classe, Departement, Etudiant, Matiere, Niveau, Note, Specialite


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display = ("nom",)
    search_fields = ("nom",)


@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    list_display = ("nom", "nombre_classes")
    search_fields = ("nom",)

    @admin.display(description="Classes")
    def nombre_classes(self, obj):
        return obj.classes.count()


@admin.register(Specialite)
class SpecialiteAdmin(admin.ModelAdmin):
    list_display = ("nom", "departement", "nombre_classes")
    list_filter = ("departement",)
    search_fields = ("nom", "departement__nom")

    @admin.display(description="Classes")
    def nombre_classes(self, obj):
        return obj.classes.count()


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ("nom", "niveau", "specialite", "departement_admin", "nombre_matieres")
    list_filter = ("niveau", "specialite__departement", "specialite")
    search_fields = ("nom", "niveau__nom", "specialite__nom", "specialite__departement__nom")

    @admin.display(description="Departement")
    def departement_admin(self, obj):
        return obj.departement

    @admin.display(description="Matieres")
    def nombre_matieres(self, obj):
        return obj.matieres.count()


@admin.register(Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    list_display = (
        "matricule",
        "nom",
        "prenom",
        "classe",
        "niveau_admin",
        "departement_admin",
        "moyenne_admin",
        "statut",
    )
    list_filter = ("classe__niveau", "classe__specialite__departement", "classe__specialite", "classe")
    search_fields = (
        "matricule",
        "nom",
        "prenom",
        "classe__nom",
        "classe__niveau__nom",
        "classe__specialite__nom",
        "classe__specialite__departement__nom",
    )

    @admin.display(description="Niveau")
    def niveau_admin(self, obj):
        return obj.niveau

    @admin.display(description="Departement")
    def departement_admin(self, obj):
        return obj.departement

    @admin.display(description="Moyenne")
    def moyenne_admin(self, obj):
        return obj.calculer_moyenne()


@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ("nom", "coefficient", "classe", "niveau_admin", "departement_admin")
    list_filter = ("classe__niveau", "classe__specialite__departement", "classe__specialite", "classe")
    search_fields = (
        "nom",
        "classe__nom",
        "classe__niveau__nom",
        "classe__specialite__nom",
        "classe__specialite__departement__nom",
    )

    @admin.display(description="Niveau")
    def niveau_admin(self, obj):
        return obj.classe.niveau

    @admin.display(description="Departement")
    def departement_admin(self, obj):
        return obj.classe.departement


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("etudiant", "matiere", "classe_admin", "valeur")
    list_filter = (
        "etudiant__classe__niveau",
        "etudiant__classe__specialite__departement",
        "etudiant__classe__specialite",
        "etudiant__classe",
        "matiere",
    )
    search_fields = (
        "etudiant__matricule",
        "etudiant__nom",
        "etudiant__prenom",
        "etudiant__classe__nom",
        "etudiant__classe__niveau__nom",
        "etudiant__classe__specialite__nom",
        "etudiant__classe__specialite__departement__nom",
        "matiere__nom",
    )

    @admin.display(description="Classe")
    def classe_admin(self, obj):
        return obj.etudiant.classe
