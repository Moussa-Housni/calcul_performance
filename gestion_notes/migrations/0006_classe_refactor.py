import django.db.models.deletion
from django.db import migrations, models


def forwards_to_classe_structure(apps, schema_editor):
    Classe = apps.get_model("gestion_notes", "Classe")
    Etudiant = apps.get_model("gestion_notes", "Etudiant")
    Matiere = apps.get_model("gestion_notes", "Matiere")
    Note = apps.get_model("gestion_notes", "Note")
    ProgrammeNiveau = apps.get_model("gestion_notes", "ProgrammeNiveau")

    classe_ids_by_pair = {}
    used_names = set()

    for etudiant in Etudiant.objects.select_related("niveau", "specialite").order_by("id"):
        key = (etudiant.niveau_id, etudiant.specialite_id)
        if key not in classe_ids_by_pair:
            base_name = f"{etudiant.niveau.nom} {etudiant.specialite.nom}"
            candidate = base_name
            suffix = 2
            while candidate in used_names:
                candidate = f"{base_name} {suffix}"
                suffix += 1

            classe = Classe.objects.create(
                nom=candidate,
                niveau_id=etudiant.niveau_id,
                specialite_id=etudiant.specialite_id,
            )
            used_names.add(candidate)
            classe_ids_by_pair[key] = classe.id

        etudiant.classe_id = classe_ids_by_pair[key]
        etudiant.save(update_fields=["classe"])

    matiere_ids_by_old_and_classe = {}
    anciennes_matieres = {
        matiere.id: matiere
        for matiere in Matiere.objects.filter(classe__isnull=True).order_by("id")
    }

    for (niveau_id, _specialite_id), classe_id in classe_ids_by_pair.items():
        matieres_du_niveau = Matiere.objects.filter(
            programmes_niveau__niveau_id=niveau_id,
            classe__isnull=True,
        ).distinct()
        for ancienne_matiere in matieres_du_niveau:
            nouvelle_matiere = Matiere.objects.create(
                classe_id=classe_id,
                nom=ancienne_matiere.nom,
                coefficient=ancienne_matiere.coefficient,
            )
            matiere_ids_by_old_and_classe[(ancienne_matiere.id, classe_id)] = nouvelle_matiere.id

    classes_by_etudiant = dict(Etudiant.objects.values_list("id", "classe_id"))

    for note in Note.objects.order_by("id"):
        classe_id = classes_by_etudiant.get(note.etudiant_id)
        if classe_id is None:
            continue

        nouvelle_matiere_id = matiere_ids_by_old_and_classe.get((note.matiere_id, classe_id))
        if nouvelle_matiere_id is None:
            ancienne_matiere = anciennes_matieres[note.matiere_id]
            nouvelle_matiere = Matiere.objects.create(
                classe_id=classe_id,
                nom=ancienne_matiere.nom,
                coefficient=ancienne_matiere.coefficient,
            )
            nouvelle_matiere_id = nouvelle_matiere.id
            matiere_ids_by_old_and_classe[(note.matiere_id, classe_id)] = nouvelle_matiere_id

        note.matiere_id = nouvelle_matiere_id
        note.save(update_fields=["matiere"])

    ProgrammeNiveau.objects.all().delete()
    Matiere.objects.filter(classe__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gestion_notes", "0005_programmeniveau_niveau_matieres_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Classe",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nom", models.CharField(max_length=150, unique=True)),
                (
                    "niveau",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="classes",
                        to="gestion_notes.niveau",
                    ),
                ),
                (
                    "specialite",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="classes",
                        to="gestion_notes.specialite",
                    ),
                ),
            ],
            options={
                "ordering": ["niveau__nom", "specialite__nom", "nom"],
            },
        ),
        migrations.AddConstraint(
            model_name="classe",
            constraint=models.UniqueConstraint(
                fields=("niveau", "specialite"),
                name="unique_classe_par_niveau_et_specialite",
            ),
        ),
        migrations.AddField(
            model_name="etudiant",
            name="classe",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="etudiants",
                to="gestion_notes.classe",
            ),
        ),
        migrations.AddField(
            model_name="matiere",
            name="classe",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="matieres",
                to="gestion_notes.classe",
            ),
        ),
        migrations.AlterModelOptions(
            name="matiere",
            options={"ordering": ["classe__nom", "nom"]},
        ),
        migrations.AlterField(
            model_name="matiere",
            name="nom",
            field=models.CharField(max_length=100),
        ),
        migrations.RunPython(
            forwards_to_classe_structure,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="etudiant",
            name="classe",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="etudiants",
                to="gestion_notes.classe",
            ),
        ),
        migrations.AlterField(
            model_name="matiere",
            name="classe",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="matieres",
                to="gestion_notes.classe",
            ),
        ),
        migrations.AddConstraint(
            model_name="matiere",
            constraint=models.UniqueConstraint(
                fields=("classe", "nom"),
                name="unique_matiere_par_classe",
            ),
        ),
        migrations.RemoveField(
            model_name="etudiant",
            name="niveau",
        ),
        migrations.RemoveField(
            model_name="etudiant",
            name="specialite",
        ),
        migrations.RemoveField(
            model_name="niveau",
            name="matieres",
        ),
        migrations.DeleteModel(
            name="ProgrammeNiveau",
        ),
    ]
