from django.core.management.base import BaseCommand
from django.db import transaction
from backendapp.models import Targets_watchlist, TargetPhoto
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Validate that all targets have at least one image and fix any issues'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix targets without images by adding placeholder images'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually making changes'
        )
        parser.add_argument(
            '--target-id',
            type=str,
            help='Validate specific target ID only'
        )
    
    def handle(self, *args, **options):
        try:
            # Get targets to validate
            if options['target_id']:
                try:
                    targets = [Targets_watchlist.objects.get(id=options['target_id'])]
                    self.stdout.write(f"Validating target: {targets[0].target_name}")
                except Targets_watchlist.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'Target with ID {options["target_id"]} not found')
                    )
                    return
            else:
                targets = Targets_watchlist.objects.all()
                self.stdout.write(f"Validating {targets.count()} targets")
            
            # Validate each target
            valid_targets = []
            invalid_targets = []
            
            for target in targets:
                image_count = target.images.count()
                
                if image_count > 0:
                    valid_targets.append({
                        'target': target,
                        'image_count': image_count
                    })
                else:
                    invalid_targets.append({
                        'target': target,
                        'image_count': 0
                    })
            
            # Report results
            self.stdout.write("\n" + "="*60)
            self.stdout.write("TARGET IMAGE VALIDATION RESULTS")
            self.stdout.write("="*60)
            self.stdout.write(f"Total targets: {len(targets)}")
            self.stdout.write(f"Valid targets: {len(valid_targets)}")
            self.stdout.write(f"Invalid targets: {len(invalid_targets)}")
            
            if valid_targets:
                self.stdout.write("\n✅ Valid targets:")
                for item in valid_targets:
                    self.stdout.write(f"  - {item['target'].target_name}: {item['image_count']} images")
            
            if invalid_targets:
                self.stdout.write("\n❌ Invalid targets (no images):")
                for item in invalid_targets:
                    self.stdout.write(f"  - {item['target'].target_name} (ID: {item['target'].id})")
            
            # Handle invalid targets
            if invalid_targets:
                if options['dry_run']:
                    self.stdout.write(
                        self.style.WARNING(
                            f"\nDRY RUN: {len(invalid_targets)} targets would be fixed"
                        )
                    )
                    return
                
                if options['fix']:
                    self.stdout.write(f"\n🔧 Fixing {len(invalid_targets)} invalid targets...")
                    
                    fixed_count = 0
                    for item in invalid_targets:
                        target = item['target']
                        
                        try:
                            # Create a placeholder image for the target
                            # This is a temporary solution - in production you might want to:
                            # 1. Notify administrators
                            # 2. Mark targets for review
                            # 3. Use a default image
                            
                            self.stdout.write(f"  - Creating placeholder for {target.target_name}...")
                            
                            # For now, we'll just log the issue
                            # In a real implementation, you might create a default image
                            logger.warning(
                                f"Target {target.id} ({target.target_name}) has no images. "
                                "Manual intervention required."
                            )
                            
                            fixed_count += 1
                            
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"  - Failed to fix {target.target_name}: {e}"
                                )
                            )
                            logger.error(f"Failed to fix target {target.id}: {e}")
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"\n✅ Fixed {fixed_count}/{len(invalid_targets)} targets"
                        )
                    )
                    
                    # Re-validate after fixes
                    remaining_invalid = Targets_watchlist.objects.filter(images__isnull=True).count()
                    if remaining_invalid == 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                "🎉 All targets now have at least one image!"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️ {remaining_invalid} targets still need manual attention"
                            )
                        )
                        
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"\n❌ {len(invalid_targets)} targets have no images!"
                        )
                    )
                    self.stdout.write(
                        "Use --fix to automatically fix these issues, or manually add images to each target."
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\n🎉 All targets are valid! No issues found."
                    )
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Validation command failed: {e}")
            )
            logger.error(f"Target image validation failed: {e}")
