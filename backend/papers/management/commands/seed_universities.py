"""Add well-known Nigerian universities (names only). Safe to run on every deploy."""

from django.core.management.base import BaseCommand

from papers.models import University

UNIVERSITIES = [
    ("Obafemi Awolowo University", "OAU"),
    ("University of Ibadan", "UI"),
    ("University of Lagos", "UNILAG"),
    ("University of Nigeria, Nsukka", "UNN"),
    ("Ahmadu Bello University", "ABU"),
    ("University of Benin", "UNIBEN"),
    ("University of Ilorin", "UNILORIN"),
    ("Lagos State University", "LASU"),
    ("Federal University of Technology, Akure", "FUTA"),
    ("Covenant University", "CU"),
]


class Command(BaseCommand):
    help = "Create starter universities."

    def handle(self, *args, **options):
        created = 0
        for name, short in UNIVERSITIES:
            _, was_created = University.objects.get_or_create(short_name=short, defaults={"name": name})
            created += was_created
        self.stdout.write(f"Seeded {created} new universit{'y' if created == 1 else 'ies'}.")
