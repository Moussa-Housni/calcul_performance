import django.db.models.deletion
from django.db import migrations, models


def attach_existing_specialites_to_default_departement(apps, schema_editor):
    Departement = apps.get_model("gestion_notes", "Departement")
    Specialite = apps.get_model("gestion_notes", "Specialite")

    departement_defaut, _ = Departement.objects.get_or_create(nom="Non defini")
    Specialite.objects.filter(departement__isnull=True).update(departement=departement_defaut)


class Migration(migrations.Migration):

    dependencies = [
        ("gestion_notes", "0003_reintroduce_matricule"),
    ]

    operations = [
        migrations.CreateModel(
            name="Departement",
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
        migrations.AlterModelOptions(
            name="specialite",
            options={"ordering": ["departement__nom", "nom"]},
        ),
        migrations.AddField(
            model_name="specialite",
            name="departement",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="specialites",
                to="gestion_notes.departement",
            ),
        ),
        migrations.RunPython(
            attach_existing_specialites_to_default_departement,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="specialite",
            name="departement",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="specialites",
                to="gestion_notes.departement",
            ),
        ),
    ]
