from django.core.management.base import BaseCommand
from backendapp.models import Targets_watchlist, Case, CustomUser, TargetPhoto
from django.utils import timezone
import random
from faker import Faker
import requests
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Populate the watchlist with random data for testing.'

    def handle(self, *args, **kwargs):
        fake = Faker()
        # Get or create a test user
        user, _ = CustomUser.objects.get_or_create(email='testuser@example.com', defaults={'is_staff': True, 'is_active': True, 'role': 'admin'})
        user.set_password('testpass123')
        user.save()
        # Create some cases
        cases = []
        for _ in range(3):
            case, _ = Case.objects.get_or_create(
                case_name=fake.bs().title(),
                defaults={
                    'description': fake.text(),
                    'created_by': user
                }
            )
            cases.append(case)
        # Create random targets with images
        for _ in range(10):
            target = Targets_watchlist.objects.create(
                case=random.choice(cases),
                target_name=fake.name(),
                target_text=fake.text(),
                target_url=fake.url(),
                target_email=fake.email(),
                target_phone=fake.phone_number(),
                case_status=random.choice([c[0] for c in Targets_watchlist.CASE_STATUS]),
                gender=random.choice([g[0] for g in Targets_watchlist.GENDER]),
                created_by=user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )
            # Add a random image (using a placeholder image service)
            img_url = f'https://picsum.photos/seed/{random.randint(1,10000)}/400/400'
            response = requests.get(img_url)
            if response.status_code == 200:
                TargetPhoto.objects.create(
                    person=target,
                    image=ContentFile(response.content, name=f"target_{target.pk}.jpg"),
                    uploaded_by=user
                )
        self.stdout.write(self.style.SUCCESS('Populated watchlist with random data and images.')) 