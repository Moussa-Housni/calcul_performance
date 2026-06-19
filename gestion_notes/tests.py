from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .forms import BulkNotesForm, ClasseForm, NoteForm
from .models import Classe, Departement, Etudiant, Matiere, Niveau, Note, Specialite


class EtudiantModelTests(TestCase):
    def setUp(self):
        self.niveau_l1 = Niveau.objects.create(nom="L1")
        self.departement = Departement.objects.create(nom="Informatique")
        self.specialite_info = Specialite.objects.create(
            nom="Developpement",
            departement=self.departement,
        )
        self.specialite_reseaux = Specialite.objects.create(
            nom="Reseaux",
            departement=self.departement,
        )
        self.classe_info = Classe.objects.create(
            niveau=self.niveau_l1,
            specialite=self.specialite_info,
            nom="temp",
        )
        self.classe_reseaux = Classe.objects.create(
            niveau=self.niveau_l1,
            specialite=self.specialite_reseaux,
            nom="temp",
        )
        self.etudiant_counter = 1

    def create_etudiant(self, classe, nom="Ali", prenom="Sami"):
        matricule = f"ETU-T-{self.etudiant_counter:03d}"
        self.etudiant_counter += 1
        return Etudiant.objects.create(
            nom=nom,
            prenom=prenom,
            matricule=matricule,
            classe=classe,
        )

    def test_calculer_moyenne_ponderee_avec_matieres_de_la_classe(self):
        etudiant = self.create_etudiant(self.classe_info)
        math = Matiere.objects.create(classe=self.classe_info, nom="Math", coefficient=4)
        algo = Matiere.objects.create(classe=self.classe_info, nom="Algo", coefficient=6)

        Note.objects.create(etudiant=etudiant, matiere=math, valeur=10)
        Note.objects.create(etudiant=etudiant, matiere=algo, valeur=20)

        self.assertEqual(etudiant.calculer_moyenne(), Decimal("16.00"))
        self.assertEqual(etudiant.statut, "Admis")

    def test_calculer_moyenne_compte_zero_pour_une_matiere_sans_note(self):
        etudiant = self.create_etudiant(self.classe_reseaux)
        math = Matiere.objects.create(classe=self.classe_reseaux, nom="Math", coefficient=4)
        algo = Matiere.objects.create(classe=self.classe_reseaux, nom="Algo", coefficient=6)
        securite = Matiere.objects.create(classe=self.classe_reseaux, nom="Securite", coefficient=2)

        Note.objects.create(etudiant=etudiant, matiere=math, valeur=10)
        Note.objects.create(etudiant=etudiant, matiere=algo, valeur=20)

        self.assertEqual(etudiant.calculer_moyenne(), Decimal("13.33"))
        self.assertEqual(etudiant.statut, "Admis")
        self.assertEqual(securite.coefficient, 2)

    def test_calculer_moyenne_retourne_none_si_classe_sans_matiere(self):
        etudiant = self.create_etudiant(self.classe_info, nom="Ben", prenom="Omar")

        self.assertIsNone(etudiant.calculer_moyenne())
        self.assertEqual(etudiant.statut, "Aucune note")

    def test_meme_niveau_mais_specialites_differentes_donnent_des_programmes_differents(self):
        etudiant_info = self.create_etudiant(self.classe_info, nom="Info", prenom="One")
        etudiant_reseaux = self.create_etudiant(self.classe_reseaux, nom="Reseaux", prenom="Two")

        math_info = Matiere.objects.create(classe=self.classe_info, nom="Math", coefficient=4)
        algo_info = Matiere.objects.create(classe=self.classe_info, nom="Algo", coefficient=6)
        math_reseaux = Matiere.objects.create(classe=self.classe_reseaux, nom="Math", coefficient=4)
        algo_reseaux = Matiere.objects.create(classe=self.classe_reseaux, nom="Algo", coefficient=6)
        Matiere.objects.create(classe=self.classe_reseaux, nom="Securite", coefficient=2)

        Note.objects.create(etudiant=etudiant_info, matiere=math_info, valeur=10)
        Note.objects.create(etudiant=etudiant_info, matiere=algo_info, valeur=20)
        Note.objects.create(etudiant=etudiant_reseaux, matiere=math_reseaux, valeur=10)
        Note.objects.create(etudiant=etudiant_reseaux, matiere=algo_reseaux, valeur=20)

        self.assertEqual(etudiant_info.calculer_moyenne(), Decimal("16.00"))
        self.assertEqual(etudiant_reseaux.calculer_moyenne(), Decimal("13.33"))

    def test_une_seule_note_par_matiere_et_par_etudiant(self):
        etudiant = self.create_etudiant(self.classe_info)
        matiere = Matiere.objects.create(classe=self.classe_info, nom="Python", coefficient=3)
        Note.objects.create(etudiant=etudiant, matiere=matiere, valeur=14)

        with self.assertRaises(IntegrityError):
            Note.objects.create(etudiant=etudiant, matiere=matiere, valeur=16)


class ClasseFormTests(TestCase):
    def setUp(self):
        self.niveau = Niveau.objects.create(nom="L1")
        self.departement_info = Departement.objects.create(nom="Informatique")
        self.departement_marketing = Departement.objects.create(nom="Marketing")
        self.specialite_dev = Specialite.objects.create(
            nom="Developpement",
            departement=self.departement_info,
        )
        self.specialite_reseaux = Specialite.objects.create(
            nom="Reseaux",
            departement=self.departement_info,
        )
        self.specialite_marketing = Specialite.objects.create(
            nom="Marketing digital",
            departement=self.departement_marketing,
        )

    def test_formulaire_classe_filtre_les_specialites_selon_le_departement(self):
        form = ClasseForm(
            data={
                "departement": self.departement_info.pk,
                "niveau": self.niveau.pk,
                "specialite": self.specialite_dev.pk,
            }
        )

        self.assertEqual(
            list(form.fields["specialite"].queryset),
            [self.specialite_dev, self.specialite_reseaux],
        )

    def test_formulaire_classe_genere_le_nom_automatiquement(self):
        form = ClasseForm(
            data={
                "departement": self.departement_info.pk,
                "niveau": self.niveau.pk,
                "specialite": self.specialite_dev.pk,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        classe = form.save()
        self.assertEqual(classe.nom, "L1 Developpement")


class NoteFormTests(TestCase):
    def setUp(self):
        self.niveau = Niveau.objects.create(nom="L1")
        self.departement = Departement.objects.create(nom="Informatique")
        self.specialite_dev = Specialite.objects.create(
            nom="Developpement",
            departement=self.departement,
        )
        self.specialite_reseaux = Specialite.objects.create(
            nom="Reseaux",
            departement=self.departement,
        )
        self.classe_dev = Classe.objects.create(
            niveau=self.niveau,
            specialite=self.specialite_dev,
            nom="temp",
        )
        self.classe_reseaux = Classe.objects.create(
            niveau=self.niveau,
            specialite=self.specialite_reseaux,
            nom="temp",
        )
        self.etudiant = Etudiant.objects.create(
            nom="Ali",
            prenom="Sami",
            matricule="ETU-N-001",
            classe=self.classe_dev,
        )
        self.matiere_dev = Matiere.objects.create(
            classe=self.classe_dev,
            nom="Algorithmique",
            coefficient=4,
        )
        self.matiere_reseaux = Matiere.objects.create(
            classe=self.classe_reseaux,
            nom="Reseaux",
            coefficient=3,
        )

    def test_formulaire_note_filtre_les_matieres_selon_la_classe_de_l_etudiant(self):
        form = NoteForm(
            data={
                "etudiant": self.etudiant.pk,
                "matiere": self.matiere_dev.pk,
                "valeur": "12",
            }
        )

        self.assertEqual(list(form.fields["matiere"].queryset), [self.matiere_dev])

    def test_formulaire_note_refuse_une_matiere_d_une_autre_classe(self):
        form = NoteForm(
            data={
                "etudiant": self.etudiant.pk,
                "matiere": self.matiere_reseaux.pk,
                "valeur": "12",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("matiere", form.errors)

    def test_formulaire_saisie_groupee_enregistre_toutes_les_notes_de_l_etudiant(self):
        matiere_bonus = Matiere.objects.create(
            classe=self.classe_dev,
            nom="Base de donnees",
            coefficient=2,
        )
        form = BulkNotesForm(
            data={
                f"matiere_{self.matiere_dev.pk}": "14",
                f"matiere_{matiere_bonus.pk}": "16.5",
            },
            etudiant=self.etudiant,
        )

        self.assertTrue(form.is_valid(), form.errors)
        resultat = form.save()

        self.assertEqual(resultat, {"saved": 2, "deleted": 0})
        self.assertEqual(Note.objects.filter(etudiant=self.etudiant).count(), 2)
        self.assertTrue(
            Note.objects.filter(
                etudiant=self.etudiant,
                matiere=self.matiere_dev,
                valeur="14",
            ).exists()
        )
        self.assertTrue(
            Note.objects.filter(
                etudiant=self.etudiant,
                matiere=matiere_bonus,
                valeur="16.5",
            ).exists()
        )

    def test_formulaire_saisie_groupee_supprime_une_note_si_le_champ_est_vide(self):
        Note.objects.create(etudiant=self.etudiant, matiere=self.matiere_dev, valeur="13")
        form = BulkNotesForm(
            data={f"matiere_{self.matiere_dev.pk}": ""},
            etudiant=self.etudiant,
        )

        self.assertTrue(form.is_valid(), form.errors)
        resultat = form.save()

        self.assertEqual(resultat, {"saved": 0, "deleted": 1})
        self.assertFalse(
            Note.objects.filter(etudiant=self.etudiant, matiere=self.matiere_dev).exists()
        )


class GestionNotesViewsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            username="admin_test",
            password="AdminPass123!",
            is_staff=True,
        )
        self.simple_user = user_model.objects.create_user(
            username="user_test",
            password="UserPass123!",
            is_staff=False,
        )
        self.niveau_l1 = Niveau.objects.create(nom="L1")
        self.niveau_l2 = Niveau.objects.create(nom="L2")
        self.departement_info = Departement.objects.create(nom="Informatique")
        self.departement_marketing = Departement.objects.create(nom="Marketing")
        self.specialite_info = Specialite.objects.create(
            nom="Developpement",
            departement=self.departement_info,
        )
        self.specialite_reseaux = Specialite.objects.create(
            nom="Reseaux",
            departement=self.departement_info,
        )
        self.specialite_marketing = Specialite.objects.create(
            nom="Marketing digital",
            departement=self.departement_marketing,
        )
        self.classe_l1_info = Classe.objects.create(
            niveau=self.niveau_l1,
            specialite=self.specialite_info,
            nom="temp",
        )
        self.classe_l1_reseaux = Classe.objects.create(
            niveau=self.niveau_l1,
            specialite=self.specialite_reseaux,
            nom="temp",
        )
        self.classe_l2_marketing = Classe.objects.create(
            niveau=self.niveau_l2,
            specialite=self.specialite_marketing,
            nom="temp",
        )
        self.etudiant_counter = 1

    def create_etudiant(self, nom, prenom, classe=None):
        matricule = f"ETU-{self.etudiant_counter:03d}"
        self.etudiant_counter += 1
        return Etudiant.objects.create(
            nom=nom,
            prenom=prenom,
            matricule=matricule,
            classe=classe or self.classe_l1_info,
        )

    def test_tableau_de_bord_repond(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("gestion_notes:tableau_de_bord"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tableau de bord administrateur")

    def test_tableau_de_bord_affiche_les_statistiques_avancees(self):
        self.client.force_login(self.admin_user)
        alpha = self.create_etudiant("Alpha", "Aya", self.classe_l1_info)
        bravo = self.create_etudiant("Bravo", "Bilel", self.classe_l1_info)
        charlie = self.create_etudiant("Charlie", "Cyrine", self.classe_l1_reseaux)
        delta = self.create_etudiant("Delta", "Dorra", self.classe_l2_marketing)

        math_info = Matiere.objects.create(classe=self.classe_l1_info, nom="Math", coefficient=4)
        algo_info = Matiere.objects.create(classe=self.classe_l1_info, nom="Algo", coefficient=6)
        math_reseaux = Matiere.objects.create(classe=self.classe_l1_reseaux, nom="Math", coefficient=5)
        securite_reseaux = Matiere.objects.create(
            classe=self.classe_l1_reseaux,
            nom="Securite",
            coefficient=5,
        )
        Matiere.objects.create(classe=self.classe_l2_marketing, nom="Communication", coefficient=4)
        Matiere.objects.create(classe=self.classe_l2_marketing, nom="Vente", coefficient=6)

        Note.objects.create(etudiant=alpha, matiere=math_info, valeur="18")
        Note.objects.create(etudiant=alpha, matiere=algo_info, valeur="12")
        Note.objects.create(etudiant=bravo, matiere=math_info, valeur="8")
        Note.objects.create(etudiant=bravo, matiere=algo_info, valeur="10")
        Note.objects.create(etudiant=charlie, matiere=math_reseaux, valeur="14")
        Note.objects.create(etudiant=charlie, matiere=securite_reseaux, valeur="16")

        response = self.client.get(reverse("gestion_notes:tableau_de_bord"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Taux d'admission")
        self.assertContains(response, "Statistiques par classe")
        self.assertContains(response, "Statistiques par departement")
        self.assertContains(response, "Graphique des moyennes par classe")
        self.assertEqual(response.context["moyenne_generale"], Decimal("9.65"))
        self.assertEqual(response.context["taux_admission"], Decimal("50.00"))
        self.assertEqual(
            response.context["meilleure_classe"]["classe"].pk,
            self.classe_l1_reseaux.pk,
        )
        self.assertEqual(
            response.context["stats_classes"][0]["classe"].pk,
            self.classe_l1_reseaux.pk,
        )
        self.assertEqual(
            response.context["stats_departements"][0]["departement"].pk,
            self.departement_info.pk,
        )
        self.assertEqual(response.context["stats_departements"][0]["classes_total"], 2)

    def test_creation_departement_depuis_formulaire(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse("gestion_notes:liste_departements"), {"nom": "Economie"})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Departement.objects.filter(nom="Economie").exists())

    def test_creation_niveau_depuis_formulaire(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse("gestion_notes:liste_niveaux"), {"nom": "M1"})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Niveau.objects.filter(nom="M1").exists())

    def test_creation_specialite_depuis_formulaire(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("gestion_notes:liste_specialites"),
            {
                "departement": self.departement_info.pk,
                "nom": "Securite",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Specialite.objects.filter(
                nom="Securite",
                departement=self.departement_info,
            ).exists()
        )

    def test_liste_specialites_affiche_dix_specialites_par_page(self):
        self.client.force_login(self.admin_user)
        departement_extra = Departement.objects.create(nom="Droit")
        for index in range(12):
            Specialite.objects.create(
                nom=f"Specialite {index:02d}",
                departement=departement_extra if index % 2 else self.departement_info,
            )

        response = self.client.get(reverse("gestion_notes:liste_specialites"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["specialites"]), 10)
        self.assertEqual(response.context["specialites"].paginator.per_page, 10)
        self.assertContains(response, "Page 1 sur 2")

        response_page_2 = self.client.get(
            reverse("gestion_notes:liste_specialites"),
            {"page": 2},
        )

        self.assertEqual(response_page_2.status_code, 200)
        self.assertGreaterEqual(len(response_page_2.context["specialites"]), 2)
        self.assertContains(response_page_2, "Page 2 sur 2")

    def test_creation_classe_depuis_formulaire(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("gestion_notes:liste_classes"),
            {
                "departement": self.departement_marketing.pk,
                "niveau": self.niveau_l1.pk,
                "specialite": self.specialite_marketing.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Classe.objects.filter(
                niveau=self.niveau_l1,
                specialite=self.specialite_marketing,
            ).exists()
        )

    def test_liste_classes_affiche_dix_classes_par_page(self):
        self.client.force_login(self.admin_user)
        departement_extra = Departement.objects.create(nom="Sciences")
        niveau_extra = Niveau.objects.create(nom="L3")
        for index in range(12):
            specialite = Specialite.objects.create(
                nom=f"Specialite Classe {index:02d}",
                departement=departement_extra if index % 2 else self.departement_info,
            )
            Classe.objects.create(
                niveau=niveau_extra if index % 2 else self.niveau_l1,
                specialite=specialite,
                nom="temp",
            )

        response = self.client.get(reverse("gestion_notes:liste_classes"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["classes"]), 10)
        self.assertEqual(response.context["classes"].paginator.per_page, 10)
        self.assertContains(response, "Page 1 sur 2")

        response_page_2 = self.client.get(
            reverse("gestion_notes:liste_classes"),
            {"page": 2},
        )

        self.assertEqual(response_page_2.status_code, 200)
        self.assertGreaterEqual(len(response_page_2.context["classes"]), 2)
        self.assertContains(response_page_2, "Page 2 sur 2")

    def test_creation_etudiant_depuis_formulaire(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("gestion_notes:liste_etudiants"),
            {
                "nom": "Trabelsi",
                "prenom": "Maya",
                "matricule": "ETU100",
                "classe": self.classe_l1_info.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Etudiant.objects.filter(matricule="ETU100").exists())

    def test_liste_etudiants_affiche_dix_etudiants_par_page(self):
        self.client.force_login(self.admin_user)
        for index in range(12):
            self.create_etudiant(f"Etudiant{index:02d}", "Test", self.classe_l1_info)

        response = self.client.get(reverse("gestion_notes:liste_etudiants"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["etudiants"]), 10)
        self.assertEqual(response.context["etudiants"].paginator.per_page, 10)
        self.assertContains(response, "Page 1 sur 2")

        response_page_2 = self.client.get(
            reverse("gestion_notes:liste_etudiants"),
            {"page": 2},
        )

        self.assertEqual(response_page_2.status_code, 200)
        self.assertEqual(len(response_page_2.context["etudiants"]), 2)
        self.assertContains(response_page_2, "Page 2 sur 2")

    def test_creation_matiere_depuis_formulaire(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("gestion_notes:liste_matieres"),
            {
                "classe": self.classe_l1_info.pk,
                "nom": "Base de donnees",
                "coefficient": "3",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Matiere.objects.filter(
                classe=self.classe_l1_info,
                nom="Base de donnees",
            ).exists()
        )

    def test_liste_matieres_affiche_dix_matieres_par_page(self):
        self.client.force_login(self.admin_user)
        for index in range(12):
            Matiere.objects.create(
                classe=self.classe_l1_info,
                nom=f"Matiere {index:02d}",
                coefficient=2,
            )

        response = self.client.get(reverse("gestion_notes:liste_matieres"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["matieres"]), 10)
        self.assertEqual(response.context["matieres"].paginator.per_page, 10)
        self.assertContains(response, "Page 1 sur 2")

        response_page_2 = self.client.get(
            reverse("gestion_notes:liste_matieres"),
            {"page": 2},
        )

        self.assertEqual(response_page_2.status_code, 200)
        self.assertEqual(len(response_page_2.context["matieres"]), 2)
        self.assertContains(response_page_2, "Page 2 sur 2")

    def test_creation_note_depuis_formulaire(self):
        self.client.force_login(self.admin_user)
        etudiant = self.create_etudiant("Jaziri", "Youssef", self.classe_l1_info)
        matiere = Matiere.objects.create(classe=self.classe_l1_info, nom="Python", coefficient=3)

        response = self.client.post(
            reverse("gestion_notes:liste_notes"),
            {
                "departement_selectionne": self.departement_info.pk,
                "niveau_selectionne": self.niveau_l1.pk,
                "specialite_selectionnee": self.specialite_info.pk,
                "classe_selectionnee": self.classe_l1_info.pk,
                "etudiant_selectionne": etudiant.pk,
                f"matiere_{matiere.pk}": "14.5",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            (
                f"{reverse('gestion_notes:liste_notes')}?departement={self.departement_info.pk}"
                f"&niveau={self.niveau_l1.pk}&specialite={self.specialite_info.pk}"
                f"&classe={self.classe_l1_info.pk}&etudiant={etudiant.pk}"
            ),
        )
        self.assertTrue(
            Note.objects.filter(etudiant=etudiant, matiere=matiere, valeur="14.5").exists()
        )

    def test_page_resultats_classe_les_etudiants_selon_les_matieres_de_leur_classe(self):
        self.client.force_login(self.admin_user)
        alpha = self.create_etudiant("Alpha", "Aya", self.classe_l1_info)
        bravo = self.create_etudiant("Bravo", "Bilel", self.classe_l1_reseaux)
        charlie = self.create_etudiant("Charlie", "Cyrine", self.classe_l2_marketing)

        math_info = Matiere.objects.create(classe=self.classe_l1_info, nom="Math", coefficient=4)
        algo_info = Matiere.objects.create(classe=self.classe_l1_info, nom="Algo", coefficient=6)
        math_reseaux = Matiere.objects.create(classe=self.classe_l1_reseaux, nom="Math", coefficient=4)
        algo_reseaux = Matiere.objects.create(classe=self.classe_l1_reseaux, nom="Algo", coefficient=6)
        Matiere.objects.create(classe=self.classe_l1_reseaux, nom="Securite", coefficient=2)

        Note.objects.create(etudiant=alpha, matiere=math_info, valeur="18")
        Note.objects.create(etudiant=alpha, matiere=algo_info, valeur="16")
        Note.objects.create(etudiant=bravo, matiere=math_reseaux, valeur="18")
        Note.objects.create(etudiant=bravo, matiere=algo_reseaux, valeur="16")

        response = self.client.get(reverse("gestion_notes:page_resultats"))

        self.assertEqual(response.status_code, 200)
        resultats = response.context["resultats"]
        self.assertEqual(
            [(etudiant.nom, etudiant.prenom) for etudiant in resultats],
            [("Alpha", "Aya"), ("Bravo", "Bilel"), ("Charlie", "Cyrine")],
        )
        self.assertEqual(resultats[0].moyenne, Decimal("16.80"))
        self.assertEqual(resultats[1].moyenne, Decimal("14.00"))
        self.assertIsNone(resultats[2].moyenne)

    def test_page_resultats_filtre_par_niveau(self):
        self.client.force_login(self.admin_user)
        self.create_etudiant("Akrout", "Amel", self.classe_l1_info)
        cible = self.create_etudiant("Baccar", "Bassem", self.classe_l2_marketing)

        response = self.client.get(
            reverse("gestion_notes:page_resultats"),
            {"niveau": self.niveau_l2.pk},
        )

        self.assertEqual(response.status_code, 200)
        resultats = response.context["resultats"]
        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0].pk, cible.pk)

    def test_page_resultats_filtre_par_specialite(self):
        self.client.force_login(self.admin_user)
        self.create_etudiant("Cherif", "Chedly", self.classe_l1_info)
        cible = self.create_etudiant("Douik", "Dorra", self.classe_l1_reseaux)

        response = self.client.get(
            reverse("gestion_notes:page_resultats"),
            {"specialite": self.specialite_reseaux.pk},
        )

        self.assertEqual(response.status_code, 200)
        resultats = response.context["resultats"]
        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0].pk, cible.pk)

    def test_page_resultats_filtre_par_classe(self):
        self.client.force_login(self.admin_user)
        self.create_etudiant("Cherif", "Chedly", self.classe_l1_info)
        cible = self.create_etudiant("Douik", "Dorra", self.classe_l1_reseaux)

        response = self.client.get(
            reverse("gestion_notes:page_resultats"),
            {"classe": self.classe_l1_reseaux.pk},
        )

        self.assertEqual(response.status_code, 200)
        resultats = response.context["resultats"]
        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0].pk, cible.pk)

    def test_page_resultats_recherche_sur_le_nom_de_classe(self):
        self.client.force_login(self.admin_user)
        cible = self.create_etudiant("Haddad", "Houda", self.classe_l1_reseaux)
        self.create_etudiant("Jarraya", "Jalel", self.classe_l1_info)

        response = self.client.get(
            reverse("gestion_notes:page_resultats"),
            {"q": "L1 Reseaux"},
        )

        self.assertEqual(response.status_code, 200)
        resultats = response.context["resultats"]
        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0].pk, cible.pk)

    def test_page_resultats_limite_les_specialites_du_filtre_au_departement_selectionne(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("gestion_notes:page_resultats"),
            {"departement": self.departement_info.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["specialites"]),
            [self.specialite_info, self.specialite_reseaux],
        )
        self.assertContains(response, "specialites-data-resultats")

    def test_page_resultats_limite_les_classes_selon_les_filtres_actifs(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("gestion_notes:page_resultats"),
            {
                "departement": self.departement_info.pk,
                "niveau": self.niveau_l1.pk,
                "specialite": self.specialite_reseaux.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["classes"]), [self.classe_l1_reseaux])
        self.assertContains(response, "classes-data-resultats")

    def test_liste_notes_filtre_par_classe(self):
        self.client.force_login(self.admin_user)
        etudiant_info = self.create_etudiant("Info", "One", self.classe_l1_info)
        etudiant_reseaux = self.create_etudiant("Reseaux", "Two", self.classe_l1_reseaux)
        matiere_info = Matiere.objects.create(classe=self.classe_l1_info, nom="Math", coefficient=4)
        matiere_reseaux = Matiere.objects.create(classe=self.classe_l1_reseaux, nom="Securite", coefficient=2)
        Note.objects.create(etudiant=etudiant_info, matiere=matiere_info, valeur="15")
        note_cible = Note.objects.create(etudiant=etudiant_reseaux, matiere=matiere_reseaux, valeur="12")

        response = self.client.get(
            reverse("gestion_notes:liste_notes"),
            {"classe": self.classe_l1_reseaux.pk},
        )

        self.assertEqual(response.status_code, 200)
        notes = list(response.context["notes"])
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].pk, note_cible.pk)
        self.assertContains(response, self.classe_l1_reseaux.nom)

    def test_liste_notes_limite_les_options_selon_les_filtres_hierarchiques(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("gestion_notes:liste_notes"),
            {
                "departement": self.departement_info.pk,
                "niveau": self.niveau_l1.pk,
                "specialite": self.specialite_reseaux.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["specialites"]),
            [self.specialite_info, self.specialite_reseaux],
        )
        self.assertEqual(list(response.context["classes"]), [self.classe_l1_reseaux])
        self.assertContains(response, "specialites-data-notes")
        self.assertContains(response, "classes-data-notes")

    def test_liste_notes_affiche_une_fiche_groupee_pour_un_etudiant(self):
        self.client.force_login(self.admin_user)
        etudiant_alpha = self.create_etudiant("Alpha", "Aya", self.classe_l1_info)
        etudiant_bravo = self.create_etudiant("Bravo", "Bilel", self.classe_l1_info)
        Matiere.objects.create(classe=self.classe_l1_info, nom="Math", coefficient=4)
        Matiere.objects.create(classe=self.classe_l1_info, nom="Algo", coefficient=6)

        response = self.client.get(
            reverse("gestion_notes:liste_notes"),
            {
                "classe": self.classe_l1_info.pk,
                "etudiant": etudiant_alpha.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["etudiant_selectionne_obj"].pk, etudiant_alpha.pk)
        self.assertEqual(response.context["etudiant_suivant"].pk, etudiant_bravo.pk)
        self.assertEqual(len(response.context["note_form_rows"]), 2)
        self.assertContains(response, "Enregistrer toutes les notes")
        self.assertContains(response, "Enregistrer et passer a Bravo Bilel")

    def test_liste_notes_enregistre_toutes_les_notes_et_passe_a_l_etudiant_suivant(self):
        self.client.force_login(self.admin_user)
        etudiant_alpha = self.create_etudiant("Alpha", "Aya", self.classe_l1_info)
        etudiant_bravo = self.create_etudiant("Bravo", "Bilel", self.classe_l1_info)
        matiere_math = Matiere.objects.create(classe=self.classe_l1_info, nom="Math", coefficient=4)
        matiere_algo = Matiere.objects.create(classe=self.classe_l1_info, nom="Algo", coefficient=6)

        response = self.client.post(
            reverse("gestion_notes:liste_notes"),
            {
                "departement_selectionne": self.departement_info.pk,
                "niveau_selectionne": self.niveau_l1.pk,
                "specialite_selectionnee": self.specialite_info.pk,
                "classe_selectionnee": self.classe_l1_info.pk,
                "etudiant_selectionne": etudiant_alpha.pk,
                f"matiere_{matiere_math.pk}": "12",
                f"matiere_{matiere_algo.pk}": "15.5",
                "action": "next",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            (
                f"{reverse('gestion_notes:liste_notes')}?departement={self.departement_info.pk}"
                f"&niveau={self.niveau_l1.pk}&specialite={self.specialite_info.pk}"
                f"&classe={self.classe_l1_info.pk}&etudiant={etudiant_bravo.pk}"
            ),
        )
        self.assertTrue(
            Note.objects.filter(
                etudiant=etudiant_alpha,
                matiere=matiere_math,
                valeur="12",
            ).exists()
        )
        self.assertTrue(
            Note.objects.filter(
                etudiant=etudiant_alpha,
                matiere=matiere_algo,
                valeur="15.5",
            ).exists()
        )

    def test_suppression_classe_refusee_si_un_etudiant_l_utilise(self):
        self.client.force_login(self.admin_user)
        self.create_etudiant("Karoui", "Sarra", self.classe_l1_info)

        response = self.client.post(
            reverse("gestion_notes:supprimer_classe", args=[self.classe_l1_info.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Classe.objects.filter(pk=self.classe_l1_info.pk).exists())
        self.assertContains(
            response,
            "Impossible de supprimer cette classe car elle est encore associee a des etudiants.",
        )

    def test_page_protegee_redirige_vers_connexion_si_anonyme(self):
        response = self.client.get(reverse("gestion_notes:tableau_de_bord"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("gestion_notes:login"), response.url)

    def test_connexion_administrateur_autorisee(self):
        response = self.client.post(
            reverse("gestion_notes:login"),
            {
                "username": "admin_test",
                "password": "AdminPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("gestion_notes:tableau_de_bord"))

    def test_connexion_utilisateur_non_admin_refusee(self):
        response = self.client.post(
            reverse("gestion_notes:login"),
            {
                "username": "user_test",
                "password": "UserPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Seuls les administrateurs peuvent acceder a cette application.",
        )

    def test_utilisateur_connecte_non_admin_recoit_un_acces_refuse(self):
        self.client.force_login(self.simple_user)

        response = self.client.get(reverse("gestion_notes:tableau_de_bord"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acces refuse", status_code=403)
