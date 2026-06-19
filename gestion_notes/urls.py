from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import StaffAuthenticationForm

app_name = "gestion_notes"

urlpatterns = [
    path(
        "connexion/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=StaffAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "deconnexion/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("", views.tableau_de_bord, name="tableau_de_bord"),
    path("resultats/", views.page_resultats, name="page_resultats"),
    path("departements/", views.liste_departements, name="liste_departements"),
    path(
        "departements/<int:pk>/modifier/",
        views.modifier_departement,
        name="modifier_departement",
    ),
    path(
        "departements/<int:pk>/supprimer/",
        views.supprimer_departement,
        name="supprimer_departement",
    ),
    path("niveaux/", views.liste_niveaux, name="liste_niveaux"),
    path("niveaux/<int:pk>/modifier/", views.modifier_niveau, name="modifier_niveau"),
    path("niveaux/<int:pk>/supprimer/", views.supprimer_niveau, name="supprimer_niveau"),
    path("specialites/", views.liste_specialites, name="liste_specialites"),
    path(
        "specialites/<int:pk>/modifier/",
        views.modifier_specialite,
        name="modifier_specialite",
    ),
    path(
        "specialites/<int:pk>/supprimer/",
        views.supprimer_specialite,
        name="supprimer_specialite",
    ),
    path("classes/", views.liste_classes, name="liste_classes"),
    path("classes/<int:pk>/modifier/", views.modifier_classe, name="modifier_classe"),
    path("classes/<int:pk>/supprimer/", views.supprimer_classe, name="supprimer_classe"),
    path("etudiants/", views.liste_etudiants, name="liste_etudiants"),
    path("etudiants/<int:pk>/", views.detail_etudiant, name="detail_etudiant"),
    path("etudiants/<int:pk>/modifier/", views.modifier_etudiant, name="modifier_etudiant"),
    path("etudiants/<int:pk>/supprimer/", views.supprimer_etudiant, name="supprimer_etudiant"),
    path("matieres/", views.liste_matieres, name="liste_matieres"),
    path("matieres/<int:pk>/modifier/", views.modifier_matiere, name="modifier_matiere"),
    path("matieres/<int:pk>/supprimer/", views.supprimer_matiere, name="supprimer_matiere"),
    path("notes/", views.liste_notes, name="liste_notes"),
    path("notes/<int:pk>/modifier/", views.modifier_note, name="modifier_note"),
    path("notes/<int:pk>/supprimer/", views.supprimer_note, name="supprimer_note"),
]
