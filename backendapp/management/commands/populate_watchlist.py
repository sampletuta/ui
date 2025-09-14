from django.core.management.base import BaseCommand
from backendapp.models import Targets_watchlist, Case, CustomUser, TargetPhoto
from django.utils import timezone
import random
from faker import Faker
import requests
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Populate the watchlist with realistic person data and photos for testing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of targets to create (default: 20)'
        )
        parser.add_argument(
            '--cases',
            type=int,
            default=5,
            help='Number of cases to create (default: 5)'
        )

    def handle(self, *args, **options):
        fake = Faker()
        target_count = options['count']
        case_count = options['cases']
        
        self.stdout.write(f'Creating {case_count} cases and {target_count} targets...')
        
        # Get or create a test user
        user, created = CustomUser.objects.get_or_create(
            email='admin@clearsight.com', 
            defaults={
                'is_staff': True, 
                'is_active': True, 
                'role': 'admin',
                'first_name': 'System',
                'last_name': 'Administrator'
            }
        )
        if created:
            user.set_password('admin123')
            user.save()
            self.stdout.write(f'Created admin user: {user.email}')
        else:
            self.stdout.write(f'Using existing admin user: {user.email}')

        # Create realistic cases
        case_names = [
            "Corporate Security Investigation",
            "Public Safety Monitoring", 
            "VIP Protection Detail",
            "Event Security Assessment",
            "Surveillance Operation Alpha",
            "Threat Assessment Bravo",
            "Personnel Screening",
            "Access Control Review",
            "Security Audit 2024",
            "Incident Response Team"
        ]
        
        cases = []
        for i in range(min(case_count, len(case_names))):
            case, created = Case.objects.get_or_create(
                case_name=case_names[i],
                defaults={
                    'description': f"Comprehensive security monitoring and threat assessment case focusing on {case_names[i].lower()}.",
                    'created_by': user
                }
            )
            cases.append(case)
            if created:
                self.stdout.write(f'Created case: {case.case_name}')

        # Realistic person data with diverse backgrounds
        realistic_people = [
            {
                'name': 'Dr. Sarah Chen',
                'description': 'Senior Research Scientist at TechCorp. PhD in Computer Science from MIT. Known for AI research and cybersecurity expertise.',
                'email': 's.chen@techcorp.com',
                'phone': '+1-555-0101',
                'gender': 'female',
                'status': 'active'
            },
            {
                'name': 'Marcus Johnson',
                'description': 'Former military intelligence officer. Currently works as a private security consultant. Expert in threat assessment and surveillance.',
                'email': 'm.johnson@secureconsult.com',
                'phone': '+1-555-0102',
                'gender': 'male',
                'status': 'active'
            },
            {
                'name': 'Elena Rodriguez',
                'description': 'International business executive with extensive travel history. Speaks 4 languages fluently. High-profile client requiring protection.',
                'email': 'e.rodriguez@globalcorp.com',
                'phone': '+1-555-0103',
                'gender': 'female',
                'status': 'pending'
            },
            {
                'name': 'James Thompson',
                'description': 'Financial analyst at major investment bank. Involved in high-value transactions. Subject of routine security monitoring.',
                'email': 'j.thompson@investbank.com',
                'phone': '+1-555-0104',
                'gender': 'male',
                'status': 'active'
            },
            {
                'name': 'Dr. Aisha Patel',
                'description': 'Medical researcher specializing in infectious diseases. Works at CDC. Requires enhanced security due to sensitive research.',
                'email': 'a.patel@cdc.gov',
                'phone': '+1-555-0105',
                'gender': 'female',
                'status': 'active'
            },
            {
                'name': 'Robert Kim',
                'description': 'Software engineer at cybersecurity firm. Former hacker turned white-hat. Expert in penetration testing and digital forensics.',
                'email': 'r.kim@cybersec.com',
                'phone': '+1-555-0106',
                'gender': 'male',
                'status': 'in_progress'
            },
            {
                'name': 'Isabella Martinez',
                'description': 'Diplomatic attaché at embassy. Handles sensitive international relations. Requires 24/7 security monitoring.',
                'email': 'i.martinez@embassy.gov',
                'phone': '+1-555-0107',
                'gender': 'female',
                'status': 'active'
            },
            {
                'name': 'David Wilson',
                'description': 'Corporate lawyer specializing in intellectual property. Represents major tech companies in patent disputes.',
                'email': 'd.wilson@lawfirm.com',
                'phone': '+1-555-0108',
                'gender': 'male',
                'status': 'active'
            },
            {
                'name': 'Dr. Michael Brown',
                'description': 'University professor and author of several books on political science. Frequent media commentator on security issues.',
                'email': 'm.brown@university.edu',
                'phone': '+1-555-0109',
                'gender': 'male',
                'status': 'pending'
            },
            {
                'name': 'Sophia Anderson',
                'description': 'Tech startup founder and CEO. Recently raised $50M in Series B funding. High net worth individual requiring protection.',
                'email': 's.anderson@startup.io',
                'phone': '+1-555-0110',
                'gender': 'female',
                'status': 'active'
            },
            {
                'name': 'Carlos Mendez',
                'description': 'Former FBI agent now working as private investigator. Specializes in corporate espionage cases.',
                'email': 'c.mendez@privateinvest.com',
                'phone': '+1-555-0111',
                'gender': 'male',
                'status': 'active'
            },
            {
                'name': 'Dr. Jennifer Lee',
                'description': 'Nuclear physicist working at national laboratory. Handles classified research projects. Requires top-level security clearance.',
                'email': 'j.lee@nlab.gov',
                'phone': '+1-555-0112',
                'gender': 'female',
                'status': 'active'
            },
            {
                'name': 'Alexander Petrov',
                'description': 'International businessman with connections to Eastern European markets. Subject of routine monitoring due to business activities.',
                'email': 'a.petrov@globaltrade.com',
                'phone': '+1-555-0113',
                'gender': 'male',
                'status': 'pending'
            },
            {
                'name': 'Dr. Rachel Green',
                'description': 'Clinical psychologist specializing in threat assessment. Works with law enforcement on profiling cases.',
                'email': 'r.green@psychology.com',
                'phone': '+1-555-0114',
                'gender': 'female',
                'status': 'active'
            },
            {
                'name': 'Thomas O\'Connor',
                'description': 'Journalist covering national security and intelligence matters. Has published several investigative reports on government agencies.',
                'email': 't.oconnor@newspaper.com',
                'phone': '+1-555-0115',
                'gender': 'male',
                'status': 'active'
            },
            {
                'name': 'Dr. Maria Santos',
                'description': 'Environmental scientist working on climate change research. Frequently testifies before congressional committees.',
                'email': 'm.santos@environment.org',
                'phone': '+1-555-0116',
                'gender': 'female',
                'status': 'active'
            },
            {
                'name': 'Kevin Zhang',
                'description': 'Investment banker specializing in mergers and acquisitions. Handles multi-billion dollar deals for Fortune 500 companies.',
                'email': 'k.zhang@investment.com',
                'phone': '+1-555-0117',
                'gender': 'male',
                'status': 'in_progress'
            },
            {
                'name': 'Dr. Lisa Thompson',
                'description': 'Emergency medicine physician and disaster response coordinator. Works with FEMA on emergency preparedness.',
                'email': 'l.thompson@hospital.com',
                'phone': '+1-555-0118',
                'gender': 'female',
                'status': 'active'
            },
            {
                'name': 'Daniel Foster',
                'description': 'Former CIA operative now working as security consultant. Expert in counter-terrorism and threat analysis.',
                'email': 'd.foster@security.com',
                'phone': '+1-555-0119',
                'gender': 'male',
                'status': 'active'
            },
            {
                'name': 'Dr. Amanda White',
                'description': 'Biotech researcher developing new medical treatments. Works with pharmaceutical companies on drug development.',
                'email': 'a.white@biotech.com',
                'phone': '+1-555-0120',
                'gender': 'female',
                'status': 'pending'
            }
        ]

        # Create targets with realistic data
        created_targets = 0
        for i, person_data in enumerate(realistic_people[:target_count]):
            # Skip if target already exists
            if Targets_watchlist.objects.filter(target_name=person_data['name']).exists():
                self.stdout.write(f'Target {person_data["name"]} already exists, skipping...')
                continue
                
            target = Targets_watchlist.objects.create(
                case=random.choice(cases),
                target_name=person_data['name'],
                target_text=person_data['description'],
                target_email=person_data['email'],
                target_phone=person_data['phone'],
                case_status=person_data['status'],
                gender=person_data['gender'],
                created_by=user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )
            
            # Add realistic photos using different portrait services
            try:
                if person_data['gender'] == 'male':
                    photo_url = f'https://randomuser.me/api/portraits/men/{random.randint(1, 100)}.jpg'
                else:
                    photo_url = f'https://randomuser.me/api/portraits/women/{random.randint(1, 100)}.jpg'
                
                response = requests.get(photo_url, timeout=10)
                if response.status_code == 200:
                    # Create a more descriptive filename
                    safe_name = person_data['name'].replace(' ', '_').replace('.', '').replace("'", "")
                    filename = f"{safe_name}_{target.pk}.jpg"
                    
                    TargetPhoto.objects.create(
                        person=target,
                        image=ContentFile(response.content, name=filename),
                        uploaded_by=user
                    )
                    self.stdout.write(f'✓ Created target: {person_data["name"]} with photo')
                else:
                    self.stdout.write(f'⚠ Created target: {person_data["name"]} without photo (service unavailable)')
            except Exception as e:
                self.stdout.write(f'⚠ Created target: {person_data["name"]} without photo (error: {str(e)})')
            
            created_targets += 1

        # Create additional random targets if needed
        if created_targets < target_count:
            additional_needed = target_count - created_targets
            self.stdout.write(f'Creating {additional_needed} additional random targets...')
            
            for _ in range(additional_needed):
                target = Targets_watchlist.objects.create(
                    case=random.choice(cases),
                    target_name=fake.name(),
                    target_text=fake.text(max_nb_chars=200),
                    target_email=fake.email(),
                    target_phone=fake.phone_number(),
                    case_status=random.choice([c[0] for c in Targets_watchlist.CASE_STATUS]),
                    gender=random.choice([g[0] for g in Targets_watchlist.GENDER]),
                    created_by=user,
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                )
                
                # Add random photo
                try:
                    if target.gender == 'male':
                        photo_url = f'https://randomuser.me/api/portraits/men/{random.randint(1, 100)}.jpg'
                    else:
                        photo_url = f'https://randomuser.me/api/portraits/women/{random.randint(1, 100)}.jpg'
                    
                    response = requests.get(photo_url, timeout=10)
                    if response.status_code == 200:
                        TargetPhoto.objects.create(
                            person=target,
                            image=ContentFile(response.content, name=f"random_{target.pk}.jpg"),
                            uploaded_by=user
                        )
                except Exception:
                    pass
                
                created_targets += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_targets} targets across {len(cases)} cases with realistic data and photos!'
            )
        )
        
        # Display summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('SUMMARY:')
        self.stdout.write(f'Cases created: {len(cases)}')
        self.stdout.write(f'Targets created: {created_targets}')
        self.stdout.write(f'Admin user: {user.email}')
        self.stdout.write('='*50) 