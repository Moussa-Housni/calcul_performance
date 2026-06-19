from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import (
    BulkNotesForm,
    ClasseForm,
    DepartementForm,
    EtudiantForm,
    MatiereForm,
    NiveauForm,
    NoteForm,
    SpecialiteForm,
)
from .models import Classe, Departement, Etudiant, Matiere, Niveau, Note, Specialite


def administrateur_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse_lazy("gestion_notes:login"))
        if not request.user.is_staff:
            return render(request, "registration/access_denied.html", status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get_specialites_data():
    return [
        {
            "id": specialite.pk,
            "nom": specialite.nom,
            "departement_id": specialite.departement_id,
        }
        for specialite in Specialite.objects.select_related("departement")
    ]


def _get_classes_data():
    return [
        {
            "id": classe.pk,
            "nom": classe.nom,
            "departement_id": classe.specialite.departement_id,
            "niveau_id": classe.niveau_id,
            "specialite_id": classe.specialite_id,
        }
        for classe in Classe.objects.select_related("niveau", "specialite__departement")
    ]


def _get_classes_queryset(departement_id="", niveau_id="", specialite_id=""):
    classes = Classe.objects.select_related("niveau", "specialite__departement")
    departement_pk = _safe_int(departement_id)
    niveau_pk = _safe_int(niveau_id)
    specialite_pk = _safe_int(specialite_id)

    if departement_pk:
        classes = classes.filter(specialite__departement_id=departement_pk)
    if niveau_pk:
        classes = classes.filter(niveau_id=niveau_pk)
    if specialite_pk:
        classes = classes.filter(specialite_id=specialite_pk)

    return classes


def _get_etudiants_matieres_data():
    etudiants = Etudiant.objects.select_related(
        "classe__niveau",
        "classe__specialite__departement",
    ).prefetch_related("classe__matieres")
    return [
        {
            "id": etudiant.pk,
            "matieres": [
                {"id": matiere.pk, "nom": matiere.nom}
                for matiere in etudiant.classe.matieres.all()
            ],
        }
        for etudiant in etudiants
    ]


def _get_classes_etudiants_data():
    return [
        {
            "id": classe.pk,
            "etudiants": [
                {
                    "id": etudiant.pk,
                    "label": f"{etudiant.matricule} - {etudiant.nom} {etudiant.prenom}",
                }
                for etudiant in classe.etudiants.all()
            ],
        }
        for classe in Classe.objects.prefetch_related("etudiants").select_related(
            "niveau",
            "specialite__departement",
        )
    ]


def _get_notes_programme_lignes(etudiant):
    notes_par_matiere = {
        note.matiere_id: note
        for note in etudiant.notes.select_related("matiere").order_by("matiere__nom")
    }
    lignes = []

    for matiere in etudiant.classe.matieres.all():
        note = notes_par_matiere.get(matiere.pk)
        valeur = note.valeur if note else Decimal("0")
        lignes.append(
            {
                "note_obj": note,
                "matiere": matiere,
                "valeur": valeur,
                "est_absente": note is None,
                "points": (valeur * matiere.coefficient).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                ),
            }
        )

    return lignes


def _calculate_average(values):
    if not values:
        return None
    return (sum(values, Decimal("0")) / Decimal(len(values))).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _calculate_percentage(value, total):
    if value is None or not total:
        return None
    return ((Decimal(value) / Decimal(total)) * Decimal("100")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _get_annee_academique():
    today = timezone.localdate()
    start_year = today.year if today.month >= 9 else today.year - 1
    return f"{start_year}-{start_year + 1}"


def _get_etudiants_classes(
    search_query="",
    departement_id="",
    niveau_id="",
    specialite_id="",
    classe_id="",
    statut="",
):
    etudiants_qs = Etudiant.objects.select_related(
        "classe__niveau",
        "classe__specialite__departement",
    ).prefetch_related("notes__matiere", "classe__matieres")
    departement_pk = _safe_int(departement_id)
    niveau_pk = _safe_int(niveau_id)
    specialite_pk = _safe_int(specialite_id)
    classe_pk = _safe_int(classe_id)

    if departement_pk:
        etudiants_qs = etudiants_qs.filter(classe__specialite__departement_id=departement_pk)
    if niveau_pk:
        etudiants_qs = etudiants_qs.filter(classe__niveau_id=niveau_pk)
    if specialite_pk:
        etudiants_qs = etudiants_qs.filter(classe__specialite_id=specialite_pk)
    if classe_pk:
        etudiants_qs = etudiants_qs.filter(classe_id=classe_pk)
    if search_query:
        etudiants_qs = etudiants_qs.filter(
            Q(matricule__icontains=search_query)
            | Q(nom__icontains=search_query)
            | Q(prenom__icontains=search_query)
            | Q(classe__nom__icontains=search_query)
            | Q(classe__niveau__nom__icontains=search_query)
            | Q(classe__specialite__nom__icontains=search_query)
            | Q(classe__specialite__departement__nom__icontains=search_query)
        )

    etudiants = list(etudiants_qs)
    etudiants_tries = sorted(
        etudiants,
        key=lambda etudiant: etudiant.moyenne if etudiant.moyenne is not None else Decimal("-1"),
        reverse=True,
    )

    if statut == "admis":
        etudiants_tries = [etudiant for etudiant in etudiants_tries if etudiant.statut == "Admis"]
    elif statut == "non_admis":
        etudiants_tries = [etudiant for etudiant in etudiants_tries if etudiant.statut == "Non admis"]
    elif statut == "aucune_note":
        etudiants_tries = [etudiant for etudiant in etudiants_tries if etudiant.statut == "Aucune note"]

    rang = 0
    for etudiant in etudiants_tries:
        if etudiant.a_des_notes:
            rang += 1
            etudiant.rang_resultat = rang
        else:
            etudiant.rang_resultat = None

    return etudiants_tries


def _get_note_entry_state(
    classe_id="",
    etudiant_id="",
    departement_id="",
    niveau_id="",
    specialite_id="",
):
    classes = _get_classes_queryset(
        departement_id,
        niveau_id,
        specialite_id,
    ).prefetch_related("matieres", "etudiants")
    classe_selectionnee = None
    etudiants_classe = []
    etudiant_selectionne = None
    etudiant_suivant = None
    position_etudiant = None
    total_etudiants_classe = 0

    classe_pk = _safe_int(classe_id)
    etudiant_pk = _safe_int(etudiant_id)
    if classe_pk:
        classe_selectionnee = classes.filter(pk=classe_pk).first()

    if classe_selectionnee is not None:
        etudiants_classe = list(
            Etudiant.objects.filter(classe=classe_selectionnee)
            .select_related("classe__niveau", "classe__specialite__departement")
            .prefetch_related("notes__matiere", "classe__matieres")
        )
        total_etudiants_classe = len(etudiants_classe)

        if etudiants_classe:
            if etudiant_pk:
                etudiant_selectionne = next(
                    (etudiant for etudiant in etudiants_classe if etudiant.pk == etudiant_pk),
                    None,
                )
            if etudiant_selectionne is None:
                etudiant_selectionne = etudiants_classe[0]

            position_etudiant = (
                next(
                    index
                    for index, etudiant in enumerate(etudiants_classe)
                    if etudiant.pk == etudiant_selectionne.pk
                )
                + 1
            )
            if position_etudiant < total_etudiants_classe:
                etudiant_suivant = etudiants_classe[position_etudiant]

    return {
        "classes": classes,
        "classe_selectionnee_obj": classe_selectionnee,
        "etudiants_classe": etudiants_classe,
        "etudiant_selectionne_obj": etudiant_selectionne,
        "etudiant_suivant": etudiant_suivant,
        "position_etudiant": position_etudiant,
        "total_etudiants_classe": total_etudiants_classe,
    }


def _build_classe_stats(etudiants):
    stats_map = {}

    for etudiant in etudiants:
        stats = stats_map.setdefault(
            etudiant.classe_id,
            {
                "classe": etudiant.classe,
                "effectif": 0,
                "etudiants_classes": 0,
                "admis": 0,
                "non_admis": 0,
                "sans_note": 0,
                "_moyennes": [],
            },
        )
        stats["effectif"] += 1

        if etudiant.a_des_notes:
            stats["etudiants_classes"] += 1
            stats["_moyennes"].append(etudiant.moyenne)

        if etudiant.statut == "Admis":
            stats["admis"] += 1
        elif etudiant.statut == "Non admis":
            stats["non_admis"] += 1
        else:
            stats["sans_note"] += 1

    stats_classes = []
    for stats in stats_map.values():
        moyenne = _calculate_average(stats.pop("_moyennes"))
        taux_admission = _calculate_percentage(stats["admis"], stats["etudiants_classes"])
        stats["moyenne"] = moyenne
        stats["taux_admission"] = taux_admission
        stats["moyenne_barre"] = _calculate_percentage(moyenne, Decimal("20")) or Decimal(
            "0.00"
        )
        stats["taux_barre"] = taux_admission or Decimal("0.00")
        stats_classes.append(stats)

    stats_classes.sort(
        key=lambda item: (
            item["moyenne"] if item["moyenne"] is not None else Decimal("-1"),
            item["taux_admission"] if item["taux_admission"] is not None else Decimal("-1"),
            item["effectif"],
            item["admis"],
        ),
        reverse=True,
    )
    return stats_classes


def _build_departement_stats(etudiants):
    stats_map = {}

    for etudiant in etudiants:
        departement = etudiant.departement
        stats = stats_map.setdefault(
            departement.pk,
            {
                "departement": departement,
                "effectif": 0,
                "classes_total": set(),
                "etudiants_classes": 0,
                "admis": 0,
                "non_admis": 0,
                "sans_note": 0,
                "_moyennes": [],
            },
        )
        stats["effectif"] += 1
        stats["classes_total"].add(etudiant.classe_id)

        if etudiant.a_des_notes:
            stats["etudiants_classes"] += 1
            stats["_moyennes"].append(etudiant.moyenne)

        if etudiant.statut == "Admis":
            stats["admis"] += 1
        elif etudiant.statut == "Non admis":
            stats["non_admis"] += 1
        else:
            stats["sans_note"] += 1

    stats_departements = []
    for stats in stats_map.values():
        moyenne = _calculate_average(stats.pop("_moyennes"))
        taux_admission = _calculate_percentage(stats["admis"], stats["etudiants_classes"])
        stats["classes_total"] = len(stats["classes_total"])
        stats["moyenne"] = moyenne
        stats["taux_admission"] = taux_admission
        stats["moyenne_barre"] = _calculate_percentage(moyenne, Decimal("20")) or Decimal(
            "0.00"
        )
        stats["taux_barre"] = taux_admission or Decimal("0.00")
        stats_departements.append(stats)

    stats_departements.sort(
        key=lambda item: (
            item["moyenne"] if item["moyenne"] is not None else Decimal("-1"),
            item["taux_admission"] if item["taux_admission"] is not None else Decimal("-1"),
            item["effectif"],
            item["admis"],
        ),
        reverse=True,
    )
    return stats_departements


@administrateur_required
def tableau_de_bord(request):
    etudiants_tries = _get_etudiants_classes()
    notes_recentes = Note.objects.select_related(
        "etudiant__classe__niveau",
        "etudiant__classe__specialite__departement",
        "matiere__classe",
    ).order_by("-id")[:8]
    meilleur_etudiant = None

    for etudiant in etudiants_tries:
        if etudiant.moyenne is not None:
            meilleur_etudiant = etudiant
            break

    moyennes = [etudiant.moyenne for etudiant in etudiants_tries if etudiant.a_des_notes]
    total_etudiants_classes = len(moyennes)
    total_admis = sum(1 for etudiant in etudiants_tries if etudiant.statut == "Admis")
    moyenne_generale = _calculate_average(moyennes)
    taux_admission = _calculate_percentage(total_admis, total_etudiants_classes)
    stats_classes = _build_classe_stats(etudiants_tries)
    stats_departements = _build_departement_stats(etudiants_tries)
    meilleure_classe = next(
        (stats for stats in stats_classes if stats["moyenne"] is not None),
        None,
    )

    context = {
        "etudiants": etudiants_tries,
        "notes_recentes": notes_recentes,
        "total_etudiants": len(etudiants_tries),
        "total_etudiants_classes": total_etudiants_classes,
        "total_admis": total_admis,
        "total_departements": Departement.objects.count(),
        "total_niveaux": Niveau.objects.count(),
        "total_specialites": Specialite.objects.count(),
        "total_formations": Classe.objects.count(),
        "total_matieres": Matiere.objects.count(),
        "total_notes": Note.objects.count(),
        "moyenne_generale": moyenne_generale,
        "moyenne_generale_disponible": moyenne_generale is not None,
        "taux_admission": taux_admission,
        "taux_admission_disponible": taux_admission is not None,
        "meilleure_classe": meilleure_classe,
        "stats_classes": stats_classes,
        "stats_departements": stats_departements,
        "graphe_moyennes_classes": [stats for stats in stats_classes if stats["moyenne"] is not None][:6],
        "graphe_admission_departements": [
            stats for stats in stats_departements if stats["taux_admission"] is not None
        ][:6],
        "meilleur_etudiant": meilleur_etudiant,
        "annee_academique": _get_annee_academique(),
    }
    return render(request, "gestion_notes/dashboard.html", context)


@administrateur_required
def page_resultats(request):
    recherche = request.GET.get("q", "").strip()
    departement_selectionne = request.GET.get("departement", "").strip()
    niveau_selectionne = request.GET.get("niveau", "").strip()
    specialite_selectionnee = request.GET.get("specialite", "").strip()
    classe_selectionnee = request.GET.get("classe", "").strip()
    statut_selectionne = request.GET.get("statut", "").strip()
    resultats = _get_etudiants_classes(
        recherche,
        departement_selectionne,
        niveau_selectionne,
        specialite_selectionnee,
        classe_selectionnee,
        statut_selectionne,
    )
    specialites = Specialite.objects.select_related("departement")
    departement_pk = _safe_int(departement_selectionne)
    if departement_pk:
        specialites = specialites.filter(departement_id=departement_pk)
    classes = _get_classes_queryset(
        departement_selectionne,
        niveau_selectionne,
        specialite_selectionnee,
    )
    admis = sum(1 for etudiant in resultats if etudiant.statut == "Admis")
    non_admis = sum(1 for etudiant in resultats if etudiant.statut == "Non admis")
    sans_note = sum(1 for etudiant in resultats if etudiant.statut == "Aucune note")
    moyennes = [etudiant.moyenne for etudiant in resultats if etudiant.a_des_notes]
    moyenne_generale = None
    if moyennes:
        moyenne_generale = (
            sum(moyennes, Decimal("0")) / Decimal(len(moyennes))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    context = {
        "recherche": recherche,
        "departement_selectionne": departement_selectionne,
        "niveau_selectionne": niveau_selectionne,
        "specialite_selectionnee": specialite_selectionnee,
        "classe_selectionnee": classe_selectionnee,
        "statut_selectionne": statut_selectionne,
        "resultats": resultats,
        "total_resultats": len(resultats),
        "total_classes": sum(1 for etudiant in resultats if etudiant.a_des_notes),
        "total_admis": admis,
        "total_non_admis": non_admis,
        "total_sans_note": sans_note,
        "moyenne_generale": moyenne_generale,
        "moyenne_generale_disponible": moyenne_generale is not None,
        "departements": Departement.objects.all(),
        "niveaux": Niveau.objects.all(),
        "specialites": specialites,
        "classes": classes,
        "specialites_data": _get_specialites_data(),
        "classes_data": _get_classes_data(),
        "statut_options": [
            ("admis", "Admis"),
            ("non_admis", "Non admis"),
            ("aucune_note", "Aucune note"),
        ],
        "filtres_actifs": bool(
            recherche
            or departement_selectionne
            or niveau_selectionne
            or specialite_selectionnee
            or classe_selectionnee
            or statut_selectionne
        ),
    }
    return render(request, "gestion_notes/resultats.html", context)


@administrateur_required
def liste_departements(request):
    form = DepartementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Le departement a ete ajoute avec succes.")
        return redirect("gestion_notes:liste_departements")

    context = {
        "form": form,
        "departements": Departement.objects.all(),
    }
    return render(request, "gestion_notes/departements.html", context)


@administrateur_required
def modifier_departement(request, pk):
    departement = get_object_or_404(Departement, pk=pk)
    form = DepartementForm(request.POST or None, instance=departement)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Le departement a ete modifie avec succes.")
        return redirect("gestion_notes:liste_departements")

    context = {
        "form": form,
        "title": "Modifier un departement",
        "description": "Mets a jour le nom de ce departement.",
        "submit_label": "Enregistrer les modifications",
        "cancel_url": "gestion_notes:liste_departements",
    }
    return render(request, "gestion_notes/form_page.html", context)


@administrateur_required
def supprimer_departement(request, pk):
    departement = get_object_or_404(Departement, pk=pk)
    if request.method == "POST":
        try:
            departement.delete()
            messages.success(request, "Le departement a ete supprime avec succes.")
        except ProtectedError:
            messages.error(
                request,
                "Impossible de supprimer ce departement car il est encore associe a des specialites.",
            )
        return redirect("gestion_notes:liste_departements")

    context = {
        "title": "Supprimer un departement",
        "description": "Cette suppression sera refusee si des specialites utilisent encore ce departement.",
        "object_label": departement.nom,
        "cancel_url": "gestion_notes:liste_departements",
    }
    return render(request, "gestion_notes/confirm_delete.html", context)


@administrateur_required
def liste_niveaux(request):
    form = NiveauForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Le niveau a ete ajoute avec succes.")
        return redirect("gestion_notes:liste_niveaux")

    context = {
        "form": form,
        "niveaux": Niveau.objects.all(),
    }
    return render(request, "gestion_notes/niveaux.html", context)


@administrateur_required
def modifier_niveau(request, pk):
    niveau = get_object_or_404(Niveau, pk=pk)
    form = NiveauForm(request.POST or None, instance=niveau)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Le niveau a ete modifie avec succes.")
        return redirect("gestion_notes:liste_niveaux")

    context = {
        "form": form,
        "title": "Modifier un niveau",
        "description": "Mets a jour le nom de ce niveau.",
        "submit_label": "Enregistrer les modifications",
        "cancel_url": "gestion_notes:liste_niveaux",
    }
    return render(request, "gestion_notes/form_page.html", context)


@administrateur_required
def supprimer_niveau(request, pk):
    niveau = get_object_or_404(Niveau, pk=pk)
    if request.method == "POST":
        try:
            niveau.delete()
            messages.success(request, "Le niveau a ete supprime avec succes.")
        except ProtectedError:
            messages.error(
                request,
                "Impossible de supprimer ce niveau car il est encore associe a des classes.",
            )
        return redirect("gestion_notes:liste_niveaux")

    context = {
        "title": "Supprimer un niveau",
        "description": "Cette suppression sera refusee si des classes utilisent encore ce niveau.",
        "object_label": niveau.nom,
        "cancel_url": "gestion_notes:liste_niveaux",
    }
    return render(request, "gestion_notes/confirm_delete.html", context)


@administrateur_required
def liste_classes(request):
    form = ClasseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La classe a ete ajoutee avec succes.")
        return redirect("gestion_notes:liste_classes")

    classes_qs = Classe.objects.select_related("niveau", "specialite__departement")
    paginator = Paginator(classes_qs, 10)
    classes = paginator.get_page(request.GET.get("page"))

    context = {
        "form": form,
        "classes": classes,
        "peut_creer_classe": Niveau.objects.exists() and Specialite.objects.exists(),
        "specialites_data": _get_specialites_data(),
    }
    return render(request, "gestion_notes/classes.html", context)


@administrateur_required
def modifier_classe(request, pk):
    classe = get_object_or_404(Classe, pk=pk)
    form = ClasseForm(request.POST or None, instance=classe)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La classe a ete modifiee avec succes.")
        return redirect("gestion_notes:liste_classes")

    context = {
        "form": form,
        "title": "Modifier une classe",
        "description": "Mets a jour le niveau ou la specialite de cette classe.",
        "submit_label": "Enregistrer les modifications",
        "cancel_url": "gestion_notes:liste_classes",
        "specialites_data": _get_specialites_data(),
    }
    return render(request, "gestion_notes/form_page.html", context)


@administrateur_required
def supprimer_classe(request, pk):
    classe = get_object_or_404(
        Classe.objects.select_related("niveau", "specialite__departement"),
        pk=pk,
    )
    if request.method == "POST":
        try:
            classe.delete()
            messages.success(request, "La classe a ete supprimee avec succes.")
        except ProtectedError:
            messages.error(
                request,
                "Impossible de supprimer cette classe car elle est encore associee a des etudiants.",
            )
        return redirect("gestion_notes:liste_classes")

    context = {
        "title": "Supprimer une classe",
        "description": "Cette suppression sera refusee si des etudiants utilisent encore cette classe.",
        "object_label": classe.nom,
        "cancel_url": "gestion_notes:liste_classes",
    }
    return render(request, "gestion_notes/confirm_delete.html", context)


@administrateur_required
def liste_specialites(request):
    form = SpecialiteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La specialite a ete ajoutee avec succes.")
        return redirect("gestion_notes:liste_specialites")

    specialites_qs = Specialite.objects.select_related("departement")
    paginator = Paginator(specialites_qs, 10)
    specialites = paginator.get_page(request.GET.get("page"))

    context = {
        "form": form,
        "specialites": specialites,
        "peut_creer_specialite": Departement.objects.exists(),
    }
    return render(request, "gestion_notes/specialites.html", context)


@administrateur_required
def modifier_specialite(request, pk):
    specialite = get_object_or_404(Specialite, pk=pk)
    form = SpecialiteForm(request.POST or None, instance=specialite)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La specialite a ete modifiee avec succes.")
        return redirect("gestion_notes:liste_specialites")

    context = {
        "form": form,
        "title": "Modifier une specialite",
        "description": "Mets a jour le departement ou le nom de cette specialite.",
        "submit_label": "Enregistrer les modifications",
        "cancel_url": "gestion_notes:liste_specialites",
    }
    return render(request, "gestion_notes/form_page.html", context)


@administrateur_required
def supprimer_specialite(request, pk):
    specialite = get_object_or_404(Specialite, pk=pk)
    if request.method == "POST":
        try:
            specialite.delete()
            messages.success(request, "La specialite a ete supprimee avec succes.")
        except ProtectedError:
            messages.error(
                request,
                "Impossible de supprimer cette specialite car elle est encore associee a des classes.",
            )
        return redirect("gestion_notes:liste_specialites")

    context = {
        "title": "Supprimer une specialite",
        "description": "Cette suppression sera refusee si des classes utilisent encore cette specialite.",
        "object_label": specialite.nom,
        "cancel_url": "gestion_notes:liste_specialites",
    }
    return render(request, "gestion_notes/confirm_delete.html", context)


@administrateur_required
def liste_etudiants(request):
    form = EtudiantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "L'etudiant a ete ajoute avec succes.")
        return redirect("gestion_notes:liste_etudiants")

    etudiants_qs = Etudiant.objects.select_related(
        "classe__niveau",
        "classe__specialite__departement",
    ).prefetch_related("notes__matiere", "classe__matieres")
    paginator = Paginator(etudiants_qs, 10)
    etudiants = paginator.get_page(request.GET.get("page"))

    context = {
        "form": form,
        "etudiants": etudiants,
        "peut_creer_etudiant": Classe.objects.exists(),
    }
    return render(request, "gestion_notes/etudiants.html", context)


@administrateur_required
def detail_etudiant(request, pk):
    etudiant = get_object_or_404(
        Etudiant.objects.select_related(
            "classe__niveau",
            "classe__specialite__departement",
        ).prefetch_related("notes__matiere", "classe__matieres"),
        pk=pk,
    )
    context = {
        "etudiant": etudiant,
        "programme_notes": _get_notes_programme_lignes(etudiant),
    }
    return render(request, "gestion_notes/etudiant_detail.html", context)


@administrateur_required
def modifier_etudiant(request, pk):
    etudiant = get_object_or_404(Etudiant, pk=pk)
    form = EtudiantForm(request.POST or None, instance=etudiant)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "L'etudiant a ete modifie avec succes.")
        return redirect("gestion_notes:detail_etudiant", pk=etudiant.pk)

    context = {
        "form": form,
        "title": "Modifier un etudiant",
        "description": "Mets a jour les informations de cet etudiant.",
        "submit_label": "Enregistrer les modifications",
        "cancel_url": "gestion_notes:detail_etudiant",
        "cancel_kwargs": {"pk": etudiant.pk},
    }
    return render(request, "gestion_notes/form_page.html", context)


@administrateur_required
def supprimer_etudiant(request, pk):
    etudiant = get_object_or_404(Etudiant, pk=pk)
    if request.method == "POST":
        etudiant.delete()
        messages.success(request, "L'etudiant a ete supprime avec succes.")
        return redirect("gestion_notes:liste_etudiants")

    context = {
        "title": "Supprimer un etudiant",
        "description": "Cette action supprimera aussi toutes les notes associees a cet etudiant.",
        "object_label": f"{etudiant.nom} {etudiant.prenom} ({etudiant.matricule}) - {etudiant.classe.nom}",
        "cancel_url": "gestion_notes:detail_etudiant",
        "cancel_kwargs": {"pk": etudiant.pk},
    }
    return render(request, "gestion_notes/confirm_delete.html", context)


@administrateur_required
def liste_matieres(request):
    form = MatiereForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La matiere a ete ajoutee avec succes.")
        return redirect("gestion_notes:liste_matieres")

    matieres_qs = Matiere.objects.select_related(
        "classe__niveau",
        "classe__specialite__departement",
    )
    paginator = Paginator(matieres_qs, 10)
    matieres = paginator.get_page(request.GET.get("page"))

    context = {
        "form": form,
        "matieres": matieres,
        "peut_creer_matiere": Classe.objects.exists(),
    }
    return render(request, "gestion_notes/matieres.html", context)


@administrateur_required
def modifier_matiere(request, pk):
    matiere = get_object_or_404(Matiere, pk=pk)
    form = MatiereForm(request.POST or None, instance=matiere)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La matiere a ete modifiee avec succes.")
        return redirect("gestion_notes:liste_matieres")

    context = {
        "form": form,
        "title": "Modifier une matiere",
        "description": "Mets a jour la classe, le nom ou le coefficient de cette matiere.",
        "submit_label": "Enregistrer les modifications",
        "cancel_url": "gestion_notes:liste_matieres",
    }
    return render(request, "gestion_notes/form_page.html", context)


@administrateur_required
def supprimer_matiere(request, pk):
    matiere = get_object_or_404(Matiere, pk=pk)
    if request.method == "POST":
        matiere.delete()
        messages.success(request, "La matiere a ete supprimee avec succes.")
        return redirect("gestion_notes:liste_matieres")

    context = {
        "title": "Supprimer une matiere",
        "description": "Cette action supprimera aussi les notes liees a cette matiere.",
        "object_label": f"{matiere.nom} - {matiere.classe.nom} (coef {matiere.coefficient})",
        "cancel_url": "gestion_notes:liste_matieres",
    }
    return render(request, "gestion_notes/confirm_delete.html", context)


@administrateur_required
def liste_notes(request):
    departement_selectionne = (
        request.POST.get("departement_selectionne")
        or request.GET.get("departement", "")
    ).strip()
    niveau_selectionne = (
        request.POST.get("niveau_selectionne")
        or request.GET.get("niveau", "")
    ).strip()
    specialite_selectionnee = (
        request.POST.get("specialite_selectionnee")
        or request.GET.get("specialite", "")
    ).strip()
    classe_selectionnee = (
        request.POST.get("classe_selectionnee")
        or request.GET.get("classe", "")
    ).strip()
    etudiant_selectionne = (
        request.POST.get("etudiant_selectionne")
        or request.GET.get("etudiant", "")
    ).strip()
    classe_pk = _safe_int(classe_selectionnee)
    note_entry_state = _get_note_entry_state(
        classe_selectionnee,
        etudiant_selectionne,
        departement_selectionne,
        niveau_selectionne,
        specialite_selectionnee,
    )
    classe_selectionnee_obj = note_entry_state["classe_selectionnee_obj"]
    if classe_selectionnee_obj is not None:
        if not departement_selectionne:
            departement_selectionne = str(classe_selectionnee_obj.specialite.departement_id)
        if not niveau_selectionne:
            niveau_selectionne = str(classe_selectionnee_obj.niveau_id)
        if not specialite_selectionnee:
            specialite_selectionnee = str(classe_selectionnee_obj.specialite_id)
    specialites = Specialite.objects.select_related("departement")
    departement_pk = _safe_int(departement_selectionne)
    if departement_pk:
        specialites = specialites.filter(departement_id=departement_pk)
    classes = _get_classes_queryset(
        departement_selectionne,
        niveau_selectionne,
        specialite_selectionnee,
    )
    notes_form = None

    if note_entry_state["etudiant_selectionne_obj"] is not None:
        notes_form = BulkNotesForm(
            request.POST or None,
            etudiant=note_entry_state["etudiant_selectionne_obj"],
        )

    note_form_rows = []
    if notes_form is not None:
        note_form_rows = [
            {
                "field": notes_form[note_field["field_name"]],
                "matiere": note_field["matiere"],
                "note_existante": note_field["note_existante"],
            }
            for note_field in notes_form.note_fields
        ]

    if request.method == "POST":
        if note_entry_state["classe_selectionnee_obj"] is None:
            messages.error(request, "Choisis d'abord une classe pour saisir les notes.")
        elif note_entry_state["etudiant_selectionne_obj"] is None:
            messages.error(request, "Choisis un etudiant pour ouvrir sa fiche de notes.")
        elif notes_form is not None and notes_form.is_valid():
            save_result = notes_form.save()
            saved_count = save_result["saved"]
            deleted_count = save_result["deleted"]
            if deleted_count and saved_count:
                messages.success(
                    request,
                    f"Les notes ont ete enregistrees. {saved_count} note(s) saisie(s) et {deleted_count} note(s) retiree(s).",
                )
            elif deleted_count:
                messages.success(
                    request,
                    f"La fiche a ete mise a jour. {deleted_count} note(s) retiree(s).",
                )
            else:
                messages.success(
                    request,
                    f"Les notes ont ete enregistrees avec succes pour {saved_count} matiere(s).",
                )

            prochain_etudiant = note_entry_state["etudiant_selectionne_obj"]
            if (
                request.POST.get("action") == "next"
                and note_entry_state["etudiant_suivant"] is not None
            ):
                prochain_etudiant = note_entry_state["etudiant_suivant"]

            query_string = urlencode(
                {
                    "departement": note_entry_state["classe_selectionnee_obj"].specialite.departement_id,
                    "niveau": note_entry_state["classe_selectionnee_obj"].niveau_id,
                    "specialite": note_entry_state["classe_selectionnee_obj"].specialite_id,
                    "classe": note_entry_state["classe_selectionnee_obj"].pk,
                    "etudiant": prochain_etudiant.pk,
                }
            )
            return redirect(
                f"{reverse_lazy('gestion_notes:liste_notes')}?{query_string}"
            )

    notes = Note.objects.select_related(
        "etudiant__classe__niveau",
        "etudiant__classe__specialite__departement",
        "matiere__classe",
    ).order_by("-id")
    if classe_pk:
        notes = notes.filter(etudiant__classe_id=classe_pk)

    context = {
        "notes_form": notes_form,
        "notes": notes,
        "departements": Departement.objects.all(),
        "niveaux": Niveau.objects.all(),
        "specialites": specialites,
        "classes": classes,
        "departement_selectionne": departement_selectionne,
        "niveau_selectionne": niveau_selectionne,
        "specialite_selectionnee": specialite_selectionnee,
        "classe_selectionnee": classe_selectionnee,
        "classe_selectionnee_obj": classe_selectionnee_obj,
        "etudiant_selectionne": etudiant_selectionne,
        "etudiant_selectionne_obj": note_entry_state["etudiant_selectionne_obj"],
        "etudiants_classe": note_entry_state["etudiants_classe"],
        "etudiant_suivant": note_entry_state["etudiant_suivant"],
        "position_etudiant": note_entry_state["position_etudiant"],
        "total_etudiants_classe": note_entry_state["total_etudiants_classe"],
        "note_form_rows": note_form_rows,
        "filtres_actifs": bool(
            departement_selectionne
            or niveau_selectionne
            or specialite_selectionnee
            or classe_selectionnee
        ),
        "specialites_data": _get_specialites_data(),
        "classes_data": _get_classes_data(),
        "classes_etudiants_data": _get_classes_etudiants_data(),
    }
    return render(request, "gestion_notes/notes.html", context)


@administrateur_required
def modifier_note(request, pk):
    note = get_object_or_404(
        Note.objects.select_related(
            "etudiant__classe__niveau",
            "etudiant__classe__specialite__departement",
            "matiere__classe",
        ),
        pk=pk,
    )
    form = NoteForm(request.POST or None, instance=note)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La note a ete modifiee avec succes.")
        return redirect("gestion_notes:liste_notes")

    context = {
        "form": form,
        "title": "Modifier une note",
        "description": "Corrige la note, l'etudiant ou la matiere si une erreur a ete saisie.",
        "submit_label": "Enregistrer les modifications",
        "cancel_url": "gestion_notes:liste_notes",
        "etudiants_matieres_data": _get_etudiants_matieres_data(),
    }
    return render(request, "gestion_notes/form_page.html", context)


@administrateur_required
def supprimer_note(request, pk):
    note = get_object_or_404(
        Note.objects.select_related(
            "etudiant__classe__niveau",
            "etudiant__classe__specialite__departement",
            "matiere__classe",
        ),
        pk=pk,
    )
    if request.method == "POST":
        note.delete()
        messages.success(request, "La note a ete supprimee avec succes.")
        return redirect("gestion_notes:liste_notes")

    context = {
        "title": "Supprimer une note",
        "description": "Cette note disparaitra du calcul de moyenne de l'etudiant.",
        "object_label": f"{note.etudiant.nom} {note.etudiant.prenom} - {note.matiere.nom} : {note.valeur}/20",
        "cancel_url": "gestion_notes:liste_notes",
    }
    return render(request, "gestion_notes/confirm_delete.html", context)
