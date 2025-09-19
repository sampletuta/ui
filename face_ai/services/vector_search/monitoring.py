"""
Metrics Collection and Monitoring

Provides comprehensive metrics collection and monitoring for the vector search service.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from .interfaces import SearchRequest, SearchResponse
from .config import config_manager

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and manages metrics for the vector search service"""
    
    def __init__(self):
        self._config = config_manager.monitoring_config
        
        # Metrics storage
        self._search_metrics: deque = deque(maxlen=10000)
        self._error_metrics: deque = deque(maxlen=1000)
        self._insert_metrics: deque = deque(maxlen=1000)
        self._delete_metrics: deque = deque(maxlen=1000)
        
        # Counters
        self._total_searches = 0
        self._total_errors = 0
        self._total_inserts = 0
        self._total_deletes = 0
        
        # Performance tracking
        self._response_times: deque = deque(maxlen=1000)
        self._throughput_history: deque = deque(maxlen=100)
        
        logger.info("MetricsCollector initialized")
    
    async def record_search_metrics(self, request: SearchRequest, response: SearchResponse) -> None:
        """Record search operation metrics"""
        try:
            self._total_searches += 1
            
            metric = {
                'timestamp': time.time(),
                'request_id': response.request_id,
                'top_k': request.top_k,
                'threshold': request.threshold,
                'metric_type': request.metric_type.value,
                'results_count': len(response.results),
                'search_time_ms': response.search_time_ms,
                'status': response.status.value,
                'has_filters': bool(request.filters)
            }
            
            self._search_metrics.append(metric)
            self._response_times.append(response.search_time_ms)
            
            # Update throughput
            await self._update_throughput()
            
            logger.debug(f"Recorded search metrics for request {response.request_id}")
            
        except Exception as e:
            logger.error(f"Error recording search metrics: {e}")
    
    async def record_error_metrics(self, request: SearchRequest, error: Exception) -> None:
        """Record error metrics"""
        try:
            self._total_errors += 1
            
            metric = {
                'timestamp': time.time(),
                'request_id': getattr(request, 'request_id', None),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'top_k': getattr(request, 'top_k', None),
                'threshold': getattr(request, 'threshold', None)
            }
            
            self._error_metrics.append(metric)
            
            logger.debug(f"Recorded error metrics: {type(error).__name__}")
            
        except Exception as e:
            logger.error(f"Error recording error metrics: {e}")
    
    async def record_insert_metrics(self, count: int) -> None:
        """Record insert operation metrics"""
        try:
            self._total_inserts += count
            
            metric = {
                'timestamp': time.time(),
                'count': count
            }
            
            self._insert_metrics.append(metric)
            
            logger.debug(f"Recorded insert metrics: {count} vectors")
            
        except Exception as e:
            logger.error(f"Error recording insert metrics: {e}")
    
    async def record_delete_metrics(self, count: int) -> None:
        """Record delete operation metrics"""
        try:
            self._total_deletes += count
            
            metric = {
                'timestamp': time.time(),
                'count': count
            }
            
            self._delete_metrics.append(metric)
            
            logger.debug(f"Recorded delete metrics: {count} vectors")
            
        except Exception as e:
            logger.error(f"Error recording delete metrics: {e}")
    
    async def _update_throughput(self) -> None:
        """Update throughput metrics"""
        try:
            now = time.time()
            minute_ago = now - 60
            
            # Count searches in the last minute
            recent_searches = sum(
                1 for metric in self._search_metrics
                if metric['timestamp'] > minute_ago
            )
            
            self._throughput_history.append({
                'timestamp': now,
                'searches_per_minute': recent_searches
            })
            
        except Exception as e:
            logger.error(f"Error updating throughput: {e}")
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        try:
            now = time.time()
            hour_ago = now - 3600
            day_ago = now - 86400
            
            # Calculate response time statistics
            response_times = list(self._response_times)
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            min_response_time = min(response_times) if response_times else 0
            
            # Calculate throughput
            recent_throughput = list(self._throughput_history)
            avg_throughput = sum(t['searches_per_minute'] for t in recent_throughput) / len(recent_throughput) if recent_throughput else 0
            
            # Count recent operations
            recent_searches = sum(1 for m in self._search_metrics if m['timestamp'] > hour_ago)
            recent_errors = sum(1 for m in self._error_metrics if m['timestamp'] > hour_ago)
            recent_inserts = sum(m['count'] for m in self._insert_metrics if m['timestamp'] > hour_ago)
            recent_deletes = sum(m['count'] for m in self._delete_metrics if m['timestamp'] > hour_ago)
            
            # Calculate error rate
            error_rate = recent_errors / max(recent_searches, 1) * 100
            
            return {
                'summary': {
                    'total_searches': self._total_searches,
                    'total_errors': self._total_errors,
                    'total_inserts': self._total_inserts,
                    'total_deletes': self._total_deletes,
                    'error_rate_percent': error_rate
                },
                'performance': {
                    'avg_response_time_ms': avg_response_time,
                    'max_response_time_ms': max_response_time,
                    'min_response_time_ms': min_response_time,
                    'avg_throughput_per_minute': avg_throughput
                },
                'recent_activity': {
                    'searches_last_hour': recent_searches,
                    'errors_last_hour': recent_errors,
                    'inserts_last_hour': recent_inserts,
                    'deletes_last_hour': recent_deletes
                },
                'collection_stats': {
                    'search_metrics_count': len(self._search_metrics),
                    'error_metrics_count': len(self._error_metrics),
                    'insert_metrics_count': len(self._insert_metrics),
                    'delete_metrics_count': len(self._delete_metrics)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {}
    
    async def get_performance_metrics(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get performance metrics for a specific time window"""
        try:
            now = time.time()
            window_start = now - (time_window_minutes * 60)
            
            # Filter metrics by time window
            window_searches = [m for m in self._search_metrics if m['timestamp'] > window_start]
            window_errors = [m for m in self._error_metrics if m['timestamp'] > window_start]
            
            if not window_searches:
                return {
                    'time_window_minutes': time_window_minutes,
                    'total_operations': 0,
                    'error_rate_percent': 0,
                    'avg_response_time_ms': 0,
                    'throughput_per_minute': 0
                }
            
            # Calculate metrics
            total_operations = len(window_searches)
            error_rate = len(window_errors) / total_operations * 100
            
            response_times = [m['search_time_ms'] for m in window_searches]
            avg_response_time = sum(response_times) / len(response_times)
            
            throughput_per_minute = total_operations / time_window_minutes
            
            return {
                'time_window_minutes': time_window_minutes,
                'total_operations': total_operations,
                'error_rate_percent': error_rate,
                'avg_response_time_ms': avg_response_time,
                'max_response_time_ms': max(response_times),
                'min_response_time_ms': min(response_times),
                'throughput_per_minute': throughput_per_minute,
                'successful_operations': total_operations - len(window_errors),
                'failed_operations': len(window_errors)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    async def get_error_analysis(self) -> Dict[str, Any]:
        """Get error analysis and breakdown"""
        try:
            if not self._error_metrics:
                return {'error_types': {}, 'recent_errors': []}
            
            # Count error types
            error_types = defaultdict(int)
            for metric in self._error_metrics:
                error_types[metric['error_type']] += 1
            
            # Get recent errors
            recent_errors = sorted(
                self._error_metrics,
                key=lambda x: x['timestamp'],
                reverse=True
            )[:10]
            
            return {
                'error_types': dict(error_types),
                'total_errors': self._total_errors,
                'recent_errors': recent_errors
            }
            
        except Exception as e:
            logger.error(f"Error getting error analysis: {e}")
            return {}
    
    async def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external monitoring systems"""
        try:
            return {
                'timestamp': time.time(),
                'summary': await self.get_metrics_summary(),
                'performance': await self.get_performance_metrics(),
                'error_analysis': await self.get_error_analysis(),
                'raw_metrics': {
                    'search_metrics': list(self._search_metrics),
                    'error_metrics': list(self._error_metrics),
                    'insert_metrics': list(self._insert_metrics),
                    'delete_metrics': list(self._delete_metrics)
                }
            }
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return {}
    
    async def reset_metrics(self) -> None:
        """Reset all metrics"""
        try:
            self._search_metrics.clear()
            self._error_metrics.clear()
            self._insert_metrics.clear()
            self._delete_metrics.clear()
            self._response_times.clear()
            self._throughput_history.clear()
            
            self._total_searches = 0
            self._total_errors = 0
            self._total_inserts = 0
            self._total_deletes = 0
            
            logger.info("Metrics reset")
            
        except Exception as e:
            logger.error(f"Error resetting metrics: {e}")
    
    async def close(self) -> None:
        """Close metrics collector and cleanup"""
        try:
            # Export final metrics before closing
            final_metrics = await self.export_metrics()
            logger.info(f"Final metrics: {final_metrics}")
            
            # Clear all data
            await self.reset_metrics()
            
            logger.info("MetricsCollector closed")
            
        except Exception as e:
            logger.error(f"Error closing MetricsCollector: {e}")
