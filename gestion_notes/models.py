from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Departement(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Niveau(models.Model):
    nom = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Specialite(models.Model):
    departement = models.ForeignKey(
        Departement,
        on_delete=models.PROTECT,
        related_name="specialites",
    )
    nom = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["departement__nom", "nom"]

    def __str__(self):
        return f"{self.nom} ({self.departement.nom})"


class Classe(models.Model):
    nom = models.CharField(max_length=150, unique=True)
    niveau = models.ForeignKey(
        Niveau,
        on_delete=models.PROTECT,
        related_name="classes",
    )
    specialite = models.ForeignKey(
        Specialite,
        on_delete=models.PROTECT,
        related_name="classes",
    )

    class Meta:
        ordering = ["niveau__nom", "specialite__nom", "nom"]
        constraints = [
            models.UniqueConstraint(
                fields=["niveau", "specialite"],
                name="unique_classe_par_niveau_et_specialite",
            )
        ]

    def save(self, *args, **kwargs):
        if self.niveau_id and self.specialite_id:
            self.nom = f"{self.niveau.nom} {self.specialite.nom}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom

    @property
    def departement(self):
        return self.specialite.departement

    @property
    def total_coefficients(self):
        return sum(matiere.coefficient for matiere in self.matieres.all())


class Etudiant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    matricule = models.CharField(max_length=50, unique=True)
    classe = models.ForeignKey(
        Classe,
        on_delete=models.PROTECT,
        related_name="etudiants",
    )

    class Meta:
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.matricule}) - {self.classe.nom}"

    @property
    def niveau(self):
        return self.classe.niveau

    @property
    def specialite(self):
        return self.classe.specialite

    @property
    def departement(self):
        return self.classe.departement

    def calculer_moyenne(self):
        matieres = list(self.classe.matieres.all())
        if not matieres:
            return None

        notes = {note.matiere_id: note.valeur for note in self.notes.all()}
        total_points = Decimal("0")
        total_coefficients = 0

        for matiere in matieres:
            total_points += notes.get(matiere.id, Decimal("0")) * matiere.coefficient
            total_coefficients += matiere.coefficient

        moyenne = total_points / Decimal(total_coefficients)
        return moyenne.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def moyenne(self):
        return self.calculer_moyenne()

    @property
    def a_des_notes(self):
        return self.moyenne is not None

    @property
    def statut(self):
        moyenne = self.moyenne
        if moyenne is None:
            return "Aucune note"
        return "Admis" if moyenne >= Decimal("10.00") else "Non admis"


class Matiere(models.Model):
    classe = models.ForeignKey(
        Classe,
        on_delete=models.CASCADE,
        related_name="matieres",
    )
    nom = models.CharField(max_length=100)
    coefficient = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    class Meta:
        ordering = ["classe__nom", "nom"]
        constraints = [
            models.UniqueConstraint(
                fields=["classe", "nom"],
                name="unique_matiere_par_classe",
            )
        ]

    def __str__(self):
        return f"{self.nom} - {self.classe.nom} (coef {self.coefficient})"


class Note(models.Model):
    etudiant = models.ForeignKey(
        Etudiant,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    matiere = models.ForeignKey(
        Matiere,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    valeur = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )

    class Meta:
        ordering = ["etudiant__nom", "etudiant__prenom", "matiere__nom"]
        constraints = [
            models.UniqueConstraint(
                fields=["etudiant", "matiere"],
                name="unique_note_par_etudiant_et_matiere",
            )
        ]

    def clean(self):
        super().clean()
        if (
            self.etudiant_id
            and self.matiere_id
            and self.matiere.classe_id != self.etudiant.classe_id
        ):
            raise ValidationError(
                {
                    "matiere": (
                        "Cette matiere n'appartient pas a la classe de cet etudiant."
                    )
                }
            )

    def __str__(self):
        return f"{self.etudiant} - {self.matiere}: {self.valeur}"
