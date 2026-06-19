import django.db.models.deletion
from django.db import migrations, models


def assign_default_niveau_specialite(apps, schema_editor):
    Niveau = apps.get_model("gestion_notes", "Niveau")
    Specialite = apps.get_model("gestion_notes", "Specialite")
    Etudiant = apps.get_model("gestion_notes", "Etudiant")

    niveau, _ = Niveau.objects.get_or_create(nom="Non defini")
    specialite, _ = Specialite.objects.get_or_create(nom="Non definie")

    Etudiant.objects.filter(niveau__isnull=True).update(niveau=niveau)
    Etudiant.objects.filter(specialite__isnull=True).update(specialite=specialite)


class Migration(migrations.Migration):

    dependencies = [
        ("gestion_notes", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Niveau",
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
                ("nom", models.CharField(max_length=50, unique=True)),
            ],
            options={
                "ordering": ["nom"],
            },
        ),
        migrations.CreateModel(
            name="Specialite",
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
                ("nom", models.CharField(max_length=100, unique=True)),
            ],
            options={
                "ordering": ["nom"],
            },
        ),
        migrations.AddField(
            model_name="etudiant",
            name="niveau",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="etudiants",
                to="gestion_notes.niveau",
            ),
        ),
        migrations.AddField(
            model_name="etudiant",
            name="specialite",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="etudiants",
                to="gestion_notes.specialite",
            ),
        ),
        migrations.RunPython(assign_default_niveau_specialite, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="etudiant",
            name="niveau",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="etudiants",
                to="gestion_notes.niveau",
            ),
        ),
        migrations.AlterField(
            model_name="etudiant",
            name="specialite",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="etudiants",
                to="gestion_notes.specialite",
            ),
        ),
        migrations.RemoveField(
            model_name="etudiant",
            name="matricule",
        ),
        migrations.AlterModelOptions(
            name="note",
            options={"ordering": ["etudiant__nom", "etudiant__prenom", "matiere__nom"]},
        ),
    ]
