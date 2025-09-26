"""
Enhanced Detection Deduplication Service
Handles both storage deduplication (less strict) and alert deduplication (stricter)
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class EnhancedDeduplicationService:
    """
    Enhanced deduplication service with separate rules for storage and alerts
    """
    
    def __init__(self):
        # Configuration from settings
        self.storage_window_seconds = getattr(settings, 'STORAGE_DEDUPLICATION_WINDOW', 300)  # 5 minutes
        self.alert_window_seconds = getattr(settings, 'ALERT_DEDUPLICATION_WINDOW', 30)  # 30 seconds
        self.spatial_overlap_threshold = getattr(settings, 'SPATIAL_OVERLAP_THRESHOLD', 0.5)  # 50% overlap
        self.min_confidence_improvement = getattr(settings, 'MIN_CONFIDENCE_IMPROVEMENT', 0.05)  # 5% improvement
        self.max_alerts_per_target_per_hour = getattr(settings, 'MAX_ALERTS_PER_TARGET_PER_HOUR', 20)
        
        # Storage deduplication settings (less strict)
        self.storage_spatial_threshold = getattr(settings, 'STORAGE_SPATIAL_THRESHOLD', 0.7)  # 70% overlap for storage
        self.storage_confidence_threshold = getattr(settings, 'STORAGE_CONFIDENCE_THRESHOLD', 0.02)  # 2% improvement for storage
        
        logger.info(f"EnhancedDeduplicationService initialized - Storage: {self.storage_window_seconds}s, Alert: {self.alert_window_seconds}s")
    
    def check_storage_deduplication(self, detection_data: Dict) -> Dict:
        """
        Check if detection should be stored (less strict rules)
        Purpose: Keep complete history while avoiding excessive duplicates
        """
        try:
            target_id = detection_data['target_id']
            timestamp = detection_data['timestamp']
            confidence = detection_data['confidence']
            bounding_box = detection_data['bounding_box']
            camera_id = detection_data['camera_id']
            user_id = detection_data['user_id']
            
            detection_key = f"{target_id}:{camera_id}:{user_id}"
            
            # Check temporal deduplication (5 minutes)
            temporal_result = self._check_temporal_deduplication(
                detection_key, timestamp, self.storage_window_seconds
            )
            if not temporal_result['should_store']:
                return {
                    'should_store': False,
                    'reason': 'temporal',
                    'original_detection_id': temporal_result.get('original_detection_id')
                }
            
            # Check spatial deduplication (70% overlap threshold)
            spatial_result = self._check_spatial_deduplication(
                detection_key, bounding_box, timestamp, self.storage_spatial_threshold
            )
            if not spatial_result['should_store']:
                return {
                    'should_store': False,
                    'reason': 'spatial',
                    'original_detection_id': spatial_result.get('original_detection_id')
                }
            
            # Check confidence improvement (2% threshold)
            confidence_result = self._check_confidence_filtering(
                detection_key, confidence, timestamp, self.storage_confidence_threshold
            )
            if not confidence_result['should_store']:
                return {
                    'should_store': False,
                    'reason': 'confidence',
                    'original_detection_id': confidence_result.get('original_detection_id')
                }
            
            # All checks passed - should store
            self._record_detection_for_storage(detection_key, timestamp, confidence, bounding_box, detection_data['detection_id'])
            
            return {
                'should_store': True,
                'reason': 'new_detection'
            }
            
        except Exception as e:
            logger.error(f"Error in storage deduplication: {e}")
            return {'should_store': True, 'reason': 'error_fallback'}
    
    def check_alert_deduplication(self, detection_data: Dict) -> Dict:
        """
        Check if alert should be created (stricter rules)
        Purpose: Prevent notification spam while maintaining responsiveness
        """
        try:
            target_id = detection_data['target_id']
            timestamp = detection_data['timestamp']
            confidence = detection_data['confidence']
            bounding_box = detection_data['bounding_box']
            camera_id = detection_data['camera_id']
            user_id = detection_data['user_id']
            
            detection_key = f"{target_id}:{camera_id}:{user_id}"
            
            # Check temporal deduplication (30 seconds)
            temporal_result = self._check_temporal_deduplication(
                detection_key, timestamp, self.alert_window_seconds
            )
            if not temporal_result['should_alert']:
                return {
                    'should_alert': False,
                    'reason': 'temporal',
                    'last_alert_time': temporal_result.get('last_alert_time')
                }
            
            # Check spatial deduplication (50% overlap threshold)
            spatial_result = self._check_spatial_deduplication(
                detection_key, bounding_box, timestamp, self.spatial_overlap_threshold
            )
            if not spatial_result['should_alert']:
                return {
                    'should_alert': False,
                    'reason': 'spatial',
                    'overlapping_detection': spatial_result.get('overlapping_detection')
                }
            
            # Check confidence improvement (5% threshold)
            confidence_result = self._check_confidence_filtering(
                detection_key, confidence, timestamp, self.min_confidence_improvement
            )
            if not confidence_result['should_alert']:
                return {
                    'should_alert': False,
                    'reason': 'confidence',
                    'better_detection': confidence_result.get('better_detection')
                }
            
            # Check rate limiting
            rate_limit_result = self._check_rate_limiting(detection_key, timestamp)
            if not rate_limit_result['should_alert']:
                return {
                    'should_alert': False,
                    'reason': 'rate_limiting',
                    'alerts_this_hour': rate_limit_result.get('alerts_this_hour')
                }
            
            # All checks passed - should create alert
            self._record_detection_for_alerts(detection_key, timestamp, confidence, bounding_box)
            
            return {
                'should_alert': True,
                'reason': 'all_checks_passed'
            }
            
        except Exception as e:
            logger.error(f"Error in alert deduplication: {e}")
            return {'should_alert': True, 'reason': 'error_fallback'}
    
    def _check_temporal_deduplication(self, detection_key: str, timestamp: float, window_seconds: int) -> Dict:
        """Check temporal deduplication with configurable window"""
        try:
            cache_key = f"last_detection:{detection_key}"
            last_detection = cache.get(cache_key)
            
            if last_detection is None:
                return {'should_store': True, 'should_alert': True}
            
            time_since_last = timestamp - last_detection['timestamp']
            
            if time_since_last < window_seconds:
                return {
                    'should_store': False,
                    'should_alert': False,
                    'last_alert_time': last_detection['timestamp'],
                    'time_since_last': time_since_last,
                    'original_detection_id': last_detection.get('detection_id')
                }
            
            return {'should_store': True, 'should_alert': True}
            
        except Exception as e:
            logger.error(f"Error in temporal deduplication: {e}")
            return {'should_store': True, 'should_alert': True}
    
    def _check_spatial_deduplication(self, detection_key: str, bounding_box: Dict, timestamp: float, threshold: float) -> Dict:
        """Check spatial deduplication with configurable threshold"""
        try:
            cache_key = f"recent_bboxes:{detection_key}"
            recent_bboxes = cache.get(cache_key, [])
            
            if not recent_bboxes:
                return {'should_store': True, 'should_alert': True}
            
            # Check overlap with recent bounding boxes
            for recent_bbox_data in recent_bboxes:
                overlap = self._calculate_bbox_overlap(bounding_box, recent_bbox_data['bbox'])
                if overlap > threshold:
                    return {
                        'should_store': False,
                        'should_alert': False,
                        'overlapping_detection': recent_bbox_data,
                        'original_detection_id': recent_bbox_data.get('detection_id')
                    }
            
            return {'should_store': True, 'should_alert': True}
            
        except Exception as e:
            logger.error(f"Error in spatial deduplication: {e}")
            return {'should_store': True, 'should_alert': True}
    
    def _check_confidence_filtering(self, detection_key: str, confidence: float, timestamp: float, threshold: float) -> Dict:
        """Check confidence improvement with configurable threshold"""
        try:
            cache_key = f"recent_confidences:{detection_key}"
            recent_confidences = cache.get(cache_key, [])
            
            if not recent_confidences:
                return {'should_store': True, 'should_alert': True}
            
            # Find the best recent confidence
            best_recent_confidence = max(recent_confidences, key=lambda x: x['confidence'])['confidence']
            
            # Only proceed if confidence is significantly better
            if confidence < best_recent_confidence + threshold:
                return {
                    'should_store': False,
                    'should_alert': False,
                    'better_detection': {
                        'confidence': best_recent_confidence,
                        'timestamp': best_recent_confidence
                    },
                    'original_detection_id': max(recent_confidences, key=lambda x: x['confidence']).get('detection_id')
                }
            
            return {'should_store': True, 'should_alert': True}
            
        except Exception as e:
            logger.error(f"Error in confidence filtering: {e}")
            return {'should_store': True, 'should_alert': True}
    
    def _check_rate_limiting(self, detection_key: str, timestamp: float) -> Dict:
        """Check rate limiting for alerts"""
        try:
            hour_key = f"alerts_hour:{detection_key}:{int(timestamp // 3600)}"
            alerts_this_hour = cache.get(hour_key, 0)
            
            if alerts_this_hour >= self.max_alerts_per_target_per_hour:
                return {
                    'should_alert': False,
                    'alerts_this_hour': alerts_this_hour
                }
            
            return {'should_alert': True}
            
        except Exception as e:
            logger.error(f"Error in rate limiting: {e}")
            return {'should_alert': True}
    
    def _calculate_bbox_overlap(self, bbox1: Dict, bbox2: Dict) -> float:
        """Calculate overlap ratio between two bounding boxes"""
        try:
            # Convert to x1, y1, x2, y2 format
            x1_1, y1_1, w1, h1 = bbox1['x'], bbox1['y'], bbox1['w'], bbox1['h']
            x2_1, y2_1 = x1_1 + w1, y1_1 + h1
            
            x1_2, y1_2, w2, h2 = bbox2['x'], bbox2['y'], bbox2['w'], bbox2['h']
            x2_2, y2_2 = x1_2 + w2, y1_2 + h2
            
            # Calculate intersection
            x1_i = max(x1_1, x1_2)
            y1_i = max(y1_1, y1_2)
            x2_i = min(x2_1, x2_2)
            y2_i = min(y2_1, y2_2)
            
            if x2_i <= x1_i or y2_i <= y1_i:
                return 0.0  # No overlap
            
            intersection_area = (x2_i - x1_i) * (y2_i - y1_i)
            union_area = (w1 * h1) + (w2 * h2) - intersection_area
            
            return intersection_area / union_area if union_area > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating bbox overlap: {e}")
            return 0.0
    
    def _record_detection_for_storage(self, detection_key: str, timestamp: float, confidence: float, bounding_box: Dict, detection_id: str):
        """Record detection for storage deduplication"""
        try:
            # Update last detection time
            cache.set(f"last_detection:{detection_key}", {
                'timestamp': timestamp,
                'detection_id': detection_id
            }, self.storage_window_seconds * 2)
            
            # Update recent bounding boxes
            cache_key = f"recent_bboxes:{detection_key}"
            recent_bboxes = cache.get(cache_key, [])
            recent_bboxes.append({
                'bbox': bounding_box,
                'timestamp': timestamp,
                'confidence': confidence,
                'detection_id': detection_id
            })
            # Keep only recent bboxes (last 20 for storage)
            recent_bboxes = recent_bboxes[-20:]
            cache.set(cache_key, recent_bboxes, self.storage_window_seconds * 2)
            
            # Update recent confidences
            cache_key = f"recent_confidences:{detection_key}"
            recent_confidences = cache.get(cache_key, [])
            recent_confidences.append({
                'confidence': confidence,
                'timestamp': timestamp,
                'detection_id': detection_id
            })
            # Keep only recent confidences (last 20 for storage)
            recent_confidences = recent_confidences[-20:]
            cache.set(cache_key, recent_confidences, self.storage_window_seconds * 2)
            
        except Exception as e:
            logger.error(f"Error recording detection for storage: {e}")
    
    def _record_detection_for_alerts(self, detection_key: str, timestamp: float, confidence: float, bounding_box: Dict):
        """Record detection for alert deduplication"""
        try:
            # Update last alert time
            cache.set(f"last_alert:{detection_key}", timestamp, self.alert_window_seconds * 2)
            
            # Update rate limiting counter
            hour_key = f"alerts_hour:{detection_key}:{int(timestamp // 3600)}"
            cache.incr(hour_key, 1)
            cache.expire(hour_key, 3600)  # Expire after 1 hour
            
        except Exception as e:
            logger.error(f"Error recording detection for alerts: {e}")
    
    def get_deduplication_stats(self) -> Dict:
        """Get statistics about deduplication effectiveness"""
        try:
            return {
                'storage_window_seconds': self.storage_window_seconds,
                'alert_window_seconds': self.alert_window_seconds,
                'spatial_overlap_threshold': self.spatial_overlap_threshold,
                'storage_spatial_threshold': self.storage_spatial_threshold,
                'min_confidence_improvement': self.min_confidence_improvement,
                'storage_confidence_threshold': self.storage_confidence_threshold,
                'max_alerts_per_target_per_hour': self.max_alerts_per_target_per_hour
            }
            
        except Exception as e:
            logger.error(f"Error getting deduplication stats: {e}")
            return {}


# Global instance
enhanced_deduplication_service = EnhancedDeduplicationService()

