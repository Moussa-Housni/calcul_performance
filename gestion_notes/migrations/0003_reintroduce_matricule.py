from django.db import migrations, models


def populate_matricules(apps, schema_editor):
    Etudiant = apps.get_model("gestion_notes", "Etudiant")

    for etudiant in Etudiant.objects.filter(matricule__isnull=True).order_by("id"):
        etudiant.matricule = f"ETU{etudiant.id:04d}"
        etudiant.save(update_fields=["matricule"])


class Migration(migrations.Migration):

    dependencies = [
        ("gestion_notes", "0002_niveau_specialite_restructure_etudiant"),
    ]

    operations = [
        migrations.AddField(
            model_name="etudiant",
            name="matricule",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.RunPython(populate_matricules, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="etudiant",
            name="matricule",
            field=models.CharField(max_length=50, unique=True),
        ),
    ]
