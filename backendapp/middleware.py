"""
Session Monitoring Middleware
Provides comprehensive session tracking, timeout warnings, and activity logging
"""

import logging
import time
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponseForbidden
from django.core.cache import cache
import hashlib

logger = logging.getLogger('session_monitoring')

class SecurityMiddleware:
    """
    Comprehensive security middleware that provides additional security layers
    beyond Django's built-in security middlewares.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Security checks before processing request
        security_check = self._perform_security_checks(request)
        if security_check:
            return security_check
        
        # Process request
        response = self.get_response(request)
        
        # Add security headers to response
        response = self._add_security_headers(response)
        
        return response
    
    def _perform_security_checks(self, request):
        """Perform various security checks"""
        try:
            # Rate limiting check
            if self._is_rate_limited(request):
                logger.warning(f"Rate limit exceeded for IP: {self._get_client_ip(request)}")
                return HttpResponseForbidden("Rate limit exceeded. Please try again later.")
            
            # Suspicious activity check
            if self._is_suspicious_activity(request):
                logger.warning(f"Suspicious activity detected from IP: {self._get_client_ip(request)}")
                return HttpResponseForbidden("Suspicious activity detected.")
            
            # User agent validation
            if self._is_suspicious_user_agent(request):
                logger.warning(f"Suspicious user agent from IP: {self._get_client_ip(request)}")
                return HttpResponseForbidden("Invalid user agent.")
                
        except Exception as e:
            logger.error(f"Error in security checks: {e}")
        
        return None
    
    def _is_rate_limited(self, request):
        """Check if request is rate limited"""
        if not getattr(settings, 'RATELIMIT_ENABLE', False):
            return False
            
        client_ip = self._get_client_ip(request)
        cache_key = f"rate_limit:{client_ip}"
        
        # Get current request count
        request_count = cache.get(cache_key, 0)
        
        # Check if limit exceeded (100 requests per minute)
        if request_count > 100:
            return True
        
        # Increment counter
        cache.set(cache_key, request_count + 1, 60)  # 1 minute expiry
        return False
    
    def _is_suspicious_activity(self, request):
        """Check for suspicious activity patterns"""
        client_ip = self._get_client_ip(request)
        cache_key = f"suspicious:{client_ip}"
        
        # Check for rapid successive requests
        request_times = cache.get(cache_key, [])
        current_time = time.time()
        
        # Remove old timestamps (older than 1 minute)
        request_times = [t for t in request_times if current_time - t < 60]
        
        # Check if too many requests in short time
        if len(request_times) > 50:  # 50 requests per minute
            return True
        
        # Add current timestamp
        request_times.append(current_time)
        cache.set(cache_key, request_times, 60)
        
        return False
    
    def _is_suspicious_user_agent(self, request):
        """Check for suspicious user agents"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Only block completely empty user agents or obvious automated tools
        # Allow legitimate browsers and common user agents
        if not user_agent:
            return True  # Block empty user agent
        
        # Only block obvious automated tools, not legitimate browsers
        suspicious_patterns = [
            'curl',      # Command line tools
            'wget',      # Download tools
            'python-requests',  # Python requests library
            'python-urllib',    # Python urllib
            'bot',       # Generic bots
            'crawler',   # Crawlers
            'spider',    # Spiders
            'scraper',   # Scrapers
        ]
        
        user_agent_lower = user_agent.lower()
        
        # Check for suspicious patterns
        for pattern in suspicious_patterns:
            if pattern in user_agent_lower:
                return True
        
        # Allow common browser user agents
        browser_patterns = [
            'mozilla', 'chrome', 'safari', 'firefox', 'edge', 'opera',
            'webkit', 'gecko', 'trident', 'msie', 'android', 'ios'
        ]
        
        # If it contains browser patterns, allow it
        for pattern in browser_patterns:
            if pattern in user_agent_lower:
                return False
        
        # If no browser patterns found, log it but don't block (might be legitimate)
        logger.info(f"Unusual user agent detected: {user_agent[:100]}... - allowing access")
        return False
    
    def _add_security_headers(self, response):
        """Add additional security headers to response"""
        # Content Security Policy
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Additional security headers
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Remove server information
        if 'Server' in response:
            del response['Server']
        
        return response
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class SessionMonitoringMiddleware:
    """
    Middleware to monitor session activity and provide clear logging
    for session expiration, user activity, and security events.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        
        # Monitor session activity
        if hasattr(request, 'user') and request.user.is_authenticated:
            self._monitor_session_activity(request)
        
        return response
    
    def _monitor_session_activity(self, request):
        """Monitor and log session activity"""
        try:
            session = request.session
            user = request.user
            
            # Get session expiry info
            if hasattr(session, 'get_expiry_date'):
                expiry_date = session.get_expiry_date()
                if expiry_date:
                    now = timezone.now()
                    time_until_expiry = expiry_date - now
                    minutes_until_expiry = int(time_until_expiry.total_seconds() / 60)
                    
                    # Log session status
                    if minutes_until_expiry <= 5:
                        logger.warning(
                            f"Session expiring soon for user {user.email} - "
                            f"expires in {minutes_until_expiry} minutes"
                        )
                    elif minutes_until_expiry <= 15:
                        logger.info(
                            f"Session expiring soon for user {user.email} - "
                            f"expires in {minutes_until_expiry} minutes"
                        )
                    else:
                        logger.debug(
                            f"Session active for user {user.email} - "
                            f"expires in {minutes_until_expiry} minutes"
                        )
                    
                    # Log session creation time
                    if hasattr(session, 'get_expiry_age'):
                        session_age = session.get_expiry_age()
                        session_age_minutes = int(session_age / 60)
                        logger.debug(
                            f"Session age for user {user.email}: {session_age_minutes} minutes"
                        )
            
            # Log user activity
            logger.info(
                f"User {user.email} active - IP: {self._get_client_ip(request)} - "
                f"Path: {request.path}"
            )
            
        except Exception as e:
            logger.error(f"Error monitoring session activity: {e}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class SessionTimeoutMiddleware:
    """
    Middleware to handle session timeout warnings and redirects
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Check session timeout before processing
        if hasattr(request, 'user') and request.user.is_authenticated:
            self._check_session_timeout(request)
        
        response = self.get_response(request)
        return response
    
    def _check_session_timeout(self, request):
        """Check if session is about to expire and show warnings"""
        try:
            session = request.session
            
            if hasattr(session, 'get_expiry_date'):
                expiry_date = session.get_expiry_date()
                if expiry_date:
                    now = timezone.now()
                    time_until_expiry = expiry_date - now
                    seconds_until_expiry = time_until_expiry.total_seconds()
                    
                    # Add timeout warning to session
                    if seconds_until_expiry <= getattr(settings, 'SESSION_TIMEOUT_WARNING', 300):
                        request.session['timeout_warning'] = True
                        request.session['timeout_seconds'] = int(seconds_until_expiry)
                        
                        logger.warning(
                            f"Session timeout warning for user {request.user.email} - "
                            f"expires in {int(seconds_until_expiry)} seconds"
                        )
                    
                    # Force logout if session expired
                    if seconds_until_expiry <= 0:
                        from django.contrib.auth import logout
                        logout(request)
                        logger.warning(
                            f"Session expired for user {request.user.email} - forced logout"
                        )
                        
        except Exception as e:
            logger.error(f"Error checking session timeout: {e}")
