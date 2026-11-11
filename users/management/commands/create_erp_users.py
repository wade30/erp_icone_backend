
import secrets

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


USERS = [
    {
        "username": "pdg",
        "email": "pdg@erp.sn",
        "first_name": "Mamadou",
        "last_name": "Fall",
        "telephone": "+221 77 100 00 01",
        "fonction": "Président Directeur Général",
        "role": "PDG",
        "service": "GENERAL",
        "password": "Pdg@ERP2026!",
    },
    {
        "username": "directeur",
        "email": "directeur@erp.sn",
        "first_name": "Abdoulaye",
        "last_name": "Diop",
        "telephone": "+221 77 100 00 02",
        "fonction": "Directeur général",
        "role": "DIRECTOR",
        "service": "GENERAL",
        "password": "Directeur@ERP2026!",
    },
    {
        "username": "secretaire",
        "email": "secretaire@erp.sn",
        "first_name": "Aissatou",
        "last_name": "Ndiaye",
        "telephone": "+221 77 100 00 03",
        "fonction": "Secrétaire générale",
        "role": "SECRETARY",
        "service": "GENERAL",
        "password": "Secretaire@ERP2026!",
    },
    {
        "username": "financier",
        "email": "financier@erp.sn",
        "first_name": "Moussa",
        "last_name": "Sarr",
        "telephone": "+221 77 100 00 04",
        "fonction": "Responsable financier",
        "role": "FINANCE",
        "service": "GENERAL",
        "password": "Finance@ERP2026!",
    },
    {
        "username": "comptable",
        "email": "comptable@erp.sn",
        "first_name": "Fatou",
        "last_name": "Ba",
        "telephone": "+221 77 100 00 05",
        "fonction": "Comptable",
        "role": "ACCOUNTANT",
        "service": "GENERAL",
        "password": "Comptable@ERP2026!",
    },
    {
        "username": "responsable_institut",
        "email": "institut@erp.sn",
        "first_name": "Ibrahima",
        "last_name": "Diallo",
        "telephone": "+221 77 100 00 06",
        "fonction": "Responsable de l'Institut",
        "role": "SERVICE_MANAGER",
        "service": "INSTITUTE",
        "password": "Institut@ERP2026!",
    },
    {
        "username": "agent_incubateur",
        "email": "incubateur@erp.sn",
        "first_name": "Mariama",
        "last_name": "Gueye",
        "telephone": "+221 77 100 00 07",
        "fonction": "Agent de l'incubateur",
        "role": "STAFF",
        "service": "INCUBATOR",
        "password": "Incubateur@ERP2026!",
    },
    {
        "username": "tacko.hane",
        "email": "tacko.hane@erp.sn",
        "first_name": "Tacko",
        "last_name": "Hane",
        "telephone": "+221 77 100 00 08",
        "fonction": "Directrice du prescolaire",
        "role": "DIRECTOR",
        "service": "PRESCHOOL",
        "password": "Prescolaire@ERP2026!",
    },
    {
        "username": "prescolaire.enseignant1",
        "email": "prescolaire.enseignant1@erp.local",
        "first_name": "Enseignant",
        "last_name": "Préscolaire 1",
        "telephone": "",
        "fonction": "Enseignant(e) préscolaire",
        "role": "STAFF",
        "service": "PRESCHOOL",
        "password": "Prescolaire@ERP2026!",
    },
    {
        "username": "prescolaire.enseignant2",
        "email": "prescolaire.enseignant2@erp.local",
        "first_name": "Enseignant",
        "last_name": "Préscolaire 2",
        "telephone": "",
        "fonction": "Enseignant(e) préscolaire",
        "role": "STAFF",
        "service": "PRESCHOOL",
        "password": "Qu6@ojYa#N9%-4xxfpM3sQ_!",
    },
    {
        "username": "prescolaire.responsable",
        "email": "prescolaire.responsable@erp.local",
        "first_name": "Responsable",
        "last_name": "Préscolaire",
        "telephone": "",
        "fonction": "Responsable du service préscolaire",
        "role": "SERVICE_MANAGER",
        "service": "PRESCHOOL",
        "password": "Xu7_3DEvFR0AKZmNDKAe@5J2",
    },
]


class Command(BaseCommand):

    help = "Créer les 7 utilisateurs de test de l'ERP"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Réinitialiser aussi les mots de passe des comptes existants.",
        )

    def handle(self, *args, **options):

        User = get_user_model()

        reset_passwords = options["reset_passwords"]

        required_fields = {
            "username",
            "email",
            "first_name",
            "last_name",
            "telephone",
            "fonction",
            "role",
            "service",
        }

        model_fields = {
            field.name for field in User._meta.get_fields()
        }

        missing_fields = required_fields - model_fields

        if missing_fields:
            raise CommandError(
                "Champs absents du modèle utilisateur : "
                + ", ".join(sorted(missing_fields))
            )

        created_count = 0
        updated_count = 0

        for data in USERS:

            user_data = data.copy()
            password = user_data.pop("password", None)
            username = user_data["username"]

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    key: value
                    for key, value in user_data.items()
                    if key != "username"
                },
            )

            if created:
                if password is None:
                    password = secrets.token_urlsafe(24)

                # create_user garantit le hachage du mot de passe.
                user.set_password(password)
                user.save()
                created_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Utilisateur créé : {username}"
                    )
                )
                if data.get("password") is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Mot de passe temporaire pour {username} : "
                            f"{password}"
                        )
                    )

            else:
                for key, value in user_data.items():
                    setattr(user, key, value)

                if reset_passwords:
                    user.set_password(password)

                user.save()
                updated_count += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"Utilisateur mis à jour : {username}"
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Terminé : {created_count} créé(s), "
                f"{updated_count} mis à jour."
            )
        )
