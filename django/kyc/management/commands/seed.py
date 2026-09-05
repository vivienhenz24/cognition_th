from django.core.management.base import BaseCommand

from kyc.services import create_seed_users_and_pending_kyc_requests


class Command(BaseCommand):
    help = "Create the two demo users and eight pending KYC requests."

    def handle(self, *args, **options):
        created_kyc_request_count = create_seed_users_and_pending_kyc_requests()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_kyc_request_count} KYC requests created."
            )
        )
