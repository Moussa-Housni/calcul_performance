from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import Classe, Departement, Etudiant, Matiere, Niveau, Note, Specialite


INPUT_CLASS = "form-control"
SELECT_CLASS = "form-select"


def classe_label(classe):
    return (
        f"{classe.nom} - {classe.departement.nom}"
        if classe.pk
        else str(classe)
    )


class EtudiantForm(forms.ModelForm):
    class Meta:
        model = Etudiant
        fields = ["nom", "prenom", "matricule", "classe"]
        labels = {
            "nom": "Nom",
            "prenom": "Prenom",
            "matricule": "Matricule",
            "classe": "Classe",
        }
        widgets = {
            "nom": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Ex: Ben Salah"}),
            "prenom": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Ex: Ahmed"}
            ),
            "matricule": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Ex: ETU2026-001"}
            ),
            "classe": forms.Select(attrs={"class": SELECT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["classe"].queryset = Classe.objects.select_related(
            "niveau",
            "specialite__departement",
        )
        self.fields["classe"].empty_label = "Choisis une classe"
        self.fields["classe"].label_from_instance = classe_label


class NiveauForm(forms.ModelForm):
    class Meta:
        model = Niveau
        fields = ["nom"]
        labels = {"nom": "Niveau"}
        widgets = {
            "nom": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Ex: L1"})
        }


class ClasseForm(forms.ModelForm):
    departement = forms.ModelChoiceField(
        queryset=Departement.objects.none(),
        label="Departement",
        widget=forms.Select(attrs={"class": SELECT_CLASS}),
        empty_label="Choisis un departement",
    )

    class Meta:
        model = Classe
        fields = ["niveau", "specialite"]
        labels = {
            "niveau": "Niveau",
            "specialite": "Specialite",
        }
        widgets = {
            "niveau": forms.Select(attrs={"class": SELECT_CLASS}),
            "specialite": forms.Select(attrs={"class": SELECT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["departement"].queryset = Departement.objects.all()
        self.fields["specialite"].queryset = Specialite.objects.none()
        self.fields["specialite"].empty_label = "Choisis une specialite"

        departement_id = None
        if self.is_bound:
            departement_id = self.data.get(self.add_prefix("departement"))
        elif self.instance.pk and self.instance.specialite_id:
            departement_id = self.instance.specialite.departement_id
            self.initial.setdefault("departement", departement_id)

        if departement_id:
            self.fields["specialite"].queryset = Specialite.objects.filter(
                departement_id=departement_id
            ).select_related("departement")

        self.order_fields(["departement", "niveau", "specialite"])

    def clean(self):
        cleaned_data = super().clean()
        departement = cleaned_data.get("departement")
        specialite = cleaned_data.get("specialite")

        if departement and specialite and specialite.departement_id != departement.id:
            self.add_error(
                "specialite",
                "La specialite choisie ne correspond pas au departement selectionne.",
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.niveau_id and instance.specialite_id:
            instance.nom = f"{instance.niveau.nom} {instance.specialite.nom}"
        if commit:
            instance.save()
        return instance


class DepartementForm(forms.ModelForm):
    class Meta:
        model = Departement
        fields = ["nom"]
        labels = {"nom": "Departement"}
        widgets = {
            "nom": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Ex: Informatique"}
            )
        }


class SpecialiteForm(forms.ModelForm):
    class Meta:
        model = Specialite
        fields = ["departement", "nom"]
        labels = {
            "departement": "Departement",
            "nom": "Specialite",
        }
        widgets = {
            "departement": forms.Select(attrs={"class": SELECT_CLASS}),
            "nom": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Ex: Reseaux"}
            ),
        }


class MatiereForm(forms.ModelForm):
    class Meta:
        model = Matiere
        fields = ["classe", "nom", "coefficient"]
        labels = {
            "classe": "Classe",
            "nom": "Matiere",
            "coefficient": "Coefficient",
        }
        widgets = {
            "classe": forms.Select(attrs={"class": SELECT_CLASS}),
            "nom": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Ex: Mathematiques"}
            ),
            "coefficient": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": 1, "placeholder": "Ex: 4"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["classe"].queryset = Classe.objects.select_related(
            "niveau",
            "specialite__departement",
        )
        self.fields["classe"].empty_label = "Choisis une classe"
        self.fields["classe"].label_from_instance = classe_label


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["etudiant", "matiere", "valeur"]
        labels = {
            "etudiant": "Etudiant",
            "matiere": "Matiere",
            "valeur": "Note / 20",
        }
        widgets = {
            "etudiant": forms.Select(attrs={"class": SELECT_CLASS}),
            "matiere": forms.Select(attrs={"class": SELECT_CLASS}),
            "valeur": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": 0,
                    "max": 20,
                    "step": 0.25,
                    "placeholder": "Ex: 15.5",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["etudiant"].queryset = Etudiant.objects.select_related(
            "classe__niveau",
            "classe__specialite__departement",
        )
        self.fields["matiere"].queryset = Matiere.objects.none()
        self.fields["matiere"].empty_label = "Choisis une matiere"

        etudiant_id = None
        if self.is_bound:
            etudiant_id = self.data.get(self.add_prefix("etudiant"))
        elif self.instance.pk and self.instance.etudiant_id:
            etudiant_id = self.instance.etudiant_id

        if etudiant_id:
            try:
                etudiant = Etudiant.objects.select_related("classe").get(pk=etudiant_id)
            except Etudiant.DoesNotExist:
                etudiant = None

            if etudiant is not None:
                self.fields["matiere"].queryset = Matiere.objects.filter(
                    classe_id=etudiant.classe_id
                )

    def clean(self):
        cleaned_data = super().clean()
        etudiant = cleaned_data.get("etudiant")
        matiere = cleaned_data.get("matiere")

        if etudiant and matiere and matiere.classe_id != etudiant.classe_id:
            self.add_error(
                "matiere",
                "Cette matiere n'appartient pas a la classe de cet etudiant.",
            )

        return cleaned_data


class BulkNotesForm(forms.Form):
    def __init__(self, *args, etudiant=None, **kwargs):
        self.etudiant = etudiant
        self.note_fields = []
        super().__init__(*args, **kwargs)

        if not etudiant:
            return

        notes_existantes = {
            note.matiere_id: note
            for note in etudiant.notes.select_related("matiere")
        }

        for matiere in etudiant.classe.matieres.all():
            field_name = f"matiere_{matiere.pk}"
            note_existante = notes_existantes.get(matiere.pk)
            self.fields[field_name] = forms.DecimalField(
                label=matiere.nom,
                required=False,
                min_value=0,
                max_value=20,
                decimal_places=2,
                widget=forms.NumberInput(
                    attrs={
                        "class": INPUT_CLASS,
                        "min": 0,
                        "max": 20,
                        "step": 0.25,
                        "placeholder": "Laisse vide si absence de note",
                    }
                ),
            )
            self.initial[field_name] = (
                note_existante.valeur if note_existante is not None else None
            )
            self.note_fields.append(
                {
                    "field_name": field_name,
                    "matiere": matiere,
                    "note_existante": note_existante,
                }
            )

    def save(self):
        if not self.etudiant:
            return {"saved": 0, "deleted": 0}

        saved_count = 0
        deleted_count = 0

        for note_field in self.note_fields:
            field_name = note_field["field_name"]
            matiere = note_field["matiere"]
            valeur = self.cleaned_data.get(field_name)

            if valeur in (None, ""):
                deleted_count += Note.objects.filter(
                    etudiant=self.etudiant,
                    matiere=matiere,
                ).delete()[0]
                continue

            Note.objects.update_or_create(
                etudiant=self.etudiant,
                matiere=matiere,
                defaults={"valeur": valeur},
            )
            saved_count += 1

        return {"saved": saved_count, "deleted": deleted_count}


class StaffAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Nom d'utilisateur ou mot de passe incorrect.",
        "inactive": "Ce compte est inactif.",
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].label = "Nom d'utilisateur"
        self.fields["username"].widget.attrs.update(
            {
                "class": INPUT_CLASS,
                "placeholder": "Entrez votre nom d'utilisateur",
            }
        )
        self.fields["password"].label = "Mot de passe"
        self.fields["password"].widget.attrs.update(
            {
                "class": INPUT_CLASS,
                "placeholder": "Entrez votre mot de passe",
            }
        )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise ValidationError(
                "Seuls les administrateurs peuvent acceder a cette application.",
                code="not_staff",
            )
