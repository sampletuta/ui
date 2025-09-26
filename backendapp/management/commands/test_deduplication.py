"""
Management command for testing and configuring alert deduplication
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from backendapp.utils.alert_deduplication import deduplication_service
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test and configure alert deduplication system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Run deduplication tests',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show deduplication statistics',
        )
        parser.add_argument(
            '--config',
            action='store_true',
            help='Show current configuration',
        )
        parser.add_argument(
            '--simulate',
            type=int,
            metavar='N',
            help='Simulate N consecutive detections for the same target',
        )

    def handle(self, *args, **options):
        if options['test']:
            self.test_deduplication()
        elif options['stats']:
            self.show_stats()
        elif options['config']:
            self.show_config()
        elif options['simulate']:
            self.simulate_detections(options['simulate'])
        else:
            self.stdout.write(self.style.WARNING('No action specified. Use --help for options.'))

    def test_deduplication(self):
        """Test the deduplication system with sample data"""
        self.stdout.write(self.style.SUCCESS('Testing deduplication system...'))
        
        # Test data
        target_id = "test_target_123"
        camera_id = "camera_001"
        user_id = "user_001"
        
        # Simulate consecutive detections
        detections = [
            {'timestamp': time.time(), 'confidence': 0.85, 'bbox': {'x': 100, 'y': 100, 'w': 50, 'h': 50}},
            {'timestamp': time.time() + 5, 'confidence': 0.87, 'bbox': {'x': 105, 'y': 105, 'w': 50, 'h': 50}},
            {'timestamp': time.time() + 10, 'confidence': 0.82, 'bbox': {'x': 110, 'y': 110, 'w': 50, 'h': 50}},
            {'timestamp': time.time() + 15, 'confidence': 0.90, 'bbox': {'x': 115, 'y': 115, 'w': 50, 'h': 50}},
        ]
        
        alerts_created = 0
        alerts_suppressed = 0
        
        for i, detection in enumerate(detections):
            result = deduplication_service.should_create_alert(
                target_id=target_id,
                timestamp=detection['timestamp'],
                confidence=detection['confidence'],
                bounding_box=detection['bbox'],
                camera_id=camera_id,
                user_id=user_id
            )
            
            if result['should_alert']:
                alerts_created += 1
                self.stdout.write(f"Detection {i+1}: ALERT CREATED (reason: {result.get('reason')})")
            else:
                alerts_suppressed += 1
                self.stdout.write(f"Detection {i+1}: ALERT SUPPRESSED (reason: {result.get('reason')})")
        
        self.stdout.write(self.style.SUCCESS(f'\nTest Results:'))
        self.stdout.write(f'Alerts Created: {alerts_created}')
        self.stdout.write(f'Alerts Suppressed: {alerts_suppressed}')
        self.stdout.write(f'Suppression Rate: {(alerts_suppressed / len(detections)) * 100:.1f}%')

    def simulate_detections(self, count):
        """Simulate multiple consecutive detections"""
        self.stdout.write(self.style.SUCCESS(f'Simulating {count} consecutive detections...'))
        
        target_id = "sim_target_456"
        camera_id = "camera_002"
        user_id = "user_002"
        
        alerts_created = 0
        alerts_suppressed = 0
        
        for i in range(count):
            # Simulate detection every 2 seconds with slight variations
            timestamp = time.time() + (i * 2)
            confidence = 0.8 + (i % 3) * 0.05  # Vary confidence slightly
            bbox = {
                'x': 100 + (i % 5) * 2,  # Slight movement
                'y': 100 + (i % 5) * 2,
                'w': 50,
                'h': 50
            }
            
            result = deduplication_service.should_create_alert(
                target_id=target_id,
                timestamp=timestamp,
                confidence=confidence,
                bounding_box=bbox,
                camera_id=camera_id,
                user_id=user_id
            )
            
            if result['should_alert']:
                alerts_created += 1
                self.stdout.write(f"Detection {i+1}: ALERT CREATED")
            else:
                alerts_suppressed += 1
                self.stdout.write(f"Detection {i+1}: ALERT SUPPRESSED ({result.get('reason')})")
        
        self.stdout.write(self.style.SUCCESS(f'\nSimulation Results:'))
        self.stdout.write(f'Total Detections: {count}')
        self.stdout.write(f'Alerts Created: {alerts_created}')
        self.stdout.write(f'Alerts Suppressed: {alerts_suppressed}')
        self.stdout.write(f'Suppression Rate: {(alerts_suppressed / count) * 100:.1f}%')

    def show_stats(self):
        """Show deduplication statistics"""
        self.stdout.write(self.style.SUCCESS('Deduplication Statistics:'))
        
        try:
            stats = deduplication_service.get_deduplication_stats()
            for key, value in stats.items():
                self.stdout.write(f'{key}: {value}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting stats: {e}'))

    def show_config(self):
        """Show current configuration"""
        self.stdout.write(self.style.SUCCESS('Current Deduplication Configuration:'))
        
        config_items = [
            ('ALERT_TEMPORAL_WINDOW', getattr(settings, 'ALERT_TEMPORAL_WINDOW', 'Not set')),
            ('ALERT_SPATIAL_OVERLAP_THRESHOLD', getattr(settings, 'ALERT_SPATIAL_OVERLAP_THRESHOLD', 'Not set')),
            ('ALERT_MIN_CONFIDENCE_IMPROVEMENT', getattr(settings, 'ALERT_MIN_CONFIDENCE_IMPROVEMENT', 'Not set')),
            ('ALERT_MAX_PER_TARGET_PER_HOUR', getattr(settings, 'ALERT_MAX_PER_TARGET_PER_HOUR', 'Not set')),
            ('ALERT_AGGREGATION_WINDOW', getattr(settings, 'ALERT_AGGREGATION_WINDOW', 'Not set')),
        ]
        
        for key, value in config_items:
            self.stdout.write(f'{key}: {value}')
        
        self.stdout.write(self.style.WARNING('\nTo modify these settings, update your environment variables or settings.py'))

