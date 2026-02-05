from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserChartAccess, CHART_CHOICES
import os


class Command(BaseCommand):
    help = "Create admin user from .env file credentials"

    def handle(self, *args, **options):
        
        email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASSWORD")

        if not email:
            self.stderr.write(
                self.style.ERROR("ADMIN_EMAIL not found in .env file")
            )
            return

        if not password:
            self.stderr.write(
                self.style.ERROR("ADMIN_PASSWORD not found in .env file")
            )
            return

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f"User with email '{email}' already exists")
            )
            return

        # Create the admin user
        try:
            user = User.objects.create_superuser(
                username=email,
                email=email,
                password=password,
            )
            
            # Grant access to all charts
            all_chart_keys = [key for key, label in CHART_CHOICES]
            UserChartAccess.objects.create(user=user, charts=all_chart_keys)
            
            self.stdout.write(
                self.style.SUCCESS(f"Admin user '{email}' created successfully with access to all charts!")
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Failed to create admin user: {e}")
            )
