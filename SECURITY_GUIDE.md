# 🔒 Security Configuration Guide for ClearSight Face AI

## Overview
This guide provides comprehensive security hardening instructions for deploying ClearSight Face AI in production environments.

## Table of Contents
1. [Environment Setup](#environment-setup)
2. [SSL/TLS Configuration](#ssltls-configuration)
3. [Database Security](#database-security)
4. [Session Security](#session-security)
5. [Rate Limiting](#rate-limiting)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Backup and Recovery](#backup-and-recovery)
8. [Incident Response](#incident-response)

## Environment Setup

### 1. Production Environment Variables
Update your `env.production` file with secure values:

```bash
# Generate strong secrets
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Update environment file
sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" env.production
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${DB_PASSWORD}/" env.production
```

### 2. Environment Detection
The application automatically detects production mode:

```bash
export ENVIRONMENT=production
export DJANGO_SETTINGS_MODULE=backend.settings_production
```

## SSL/TLS Configuration

### 1. Obtain SSL Certificates
Use Let's Encrypt for free certificates:

```bash
# Install certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com
```

### 2. Configure HTTPS in Nginx
Update your nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # Security Headers
    add_header X-Frame-Options "DENY";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Redirect HTTP to HTTPS
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## Database Security

### 1. PostgreSQL Configuration
Create a secure database user:

```sql
-- Connect as postgres superuser
sudo -u postgres psql

-- Create database and user
CREATE DATABASE face_ai_prod;
CREATE USER face_ai_prod_user WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE face_ai_prod TO face_ai_prod_user;

-- Configure security settings
ALTER USER face_ai_prod_user CONNECTION LIMIT 10;
ALTER DATABASE face_ai_prod SET timezone = 'UTC';
```

### 2. Database SSL Connection
Configure SSL in `env.production`:

```bash
# Database SSL settings
POSTGRES_SSL_MODE=require
POSTGRES_SSL_CERT=/path/to/client.crt
POSTGRES_SSL_KEY=/path/to/client.key
POSTGRES_SSL_ROOT_CERT=/path/to/ca.crt
```

### 3. Database Backup
Set up automated backups:

```bash
# Create backup script
cat > backup_db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/face_ai"
DB_NAME="face_ai_prod"
DB_USER="face_ai_prod_user"

mkdir -p $BACKUP_DIR

pg_dump -U $DB_USER -h localhost -d $DB_NAME \
    --no-password \
    --format=custom \
    --compress=9 \
    --file=$BACKUP_DIR/backup_$DATE.dump

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.dump" -mtime +7 -delete
EOF

# Make executable and add to cron
chmod +x backup_db.sh
crontab -e
# Add: 0 2 * * * /path/to/backup_db.sh
```

## Session Security

### 1. Redis Configuration
Configure Redis with authentication:

```bash
# Redis configuration
echo "requirepass your-redis-password" >> /etc/redis/redis.conf
echo "bind 127.0.0.1" >> /etc/redis/redis.conf

# Restart Redis
sudo systemctl restart redis-server
```

### 2. Session Settings
Update session configuration in production:

```python
# In settings_production.py
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
```

## Rate Limiting

### 1. Django Rate Limiting
The application includes built-in rate limiting:

```python
# Rate limit configurations
LOGIN_RATELIMIT = '3/m'      # 3 login attempts per minute
API_RATELIMIT = '100/h'      # 100 API calls per hour
SEARCH_RATELIMIT = '30/m'    # 30 searches per minute
```

### 2. Nginx Rate Limiting
Add rate limiting to nginx:

```nginx
# Define rate limiting zones
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=3r/m;

server {
    # Apply rate limiting
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend;
    }

    location /login/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://backend;
    }
}
```

## Monitoring and Logging

### 1. Log Configuration
Production logging setup:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        },
        'security': {
            'format': '[SECURITY] %(levelname)s %(asctime)s - %(message)s',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/clearsight/django.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'security': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/clearsight/security.log',
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'security',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security'],
            'level': 'WARNING',
        },
        'backendapp': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

### 2. Health Checks
Implement health check endpoints:

```python
# In views.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache

@require_GET
@never_cache
def health_check(request):
    """Health check endpoint for monitoring"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0',
    })

@require_GET
@never_cache
def readiness_check(request):
    """Readiness check for load balancer"""
    # Check database connectivity
    try:
        from django.db import connections
        connections['default'].cursor()
        db_status = 'ok'
    except Exception:
        db_status = 'error'

    # Check Redis connectivity
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 1)
        redis_status = 'ok'
    except Exception:
        redis_status = 'error'

    status = 'ready' if db_status == 'ok' and redis_status == 'ok' else 'not ready'

    return JsonResponse({
        'status': status,
        'database': db_status,
        'redis': redis_status,
        'timestamp': timezone.now().isoformat(),
    })
```

### 3. Monitoring Setup
Install monitoring tools:

```bash
# Install Prometheus and Grafana
sudo apt install prometheus grafana

# Configure Prometheus
cat > /etc/prometheus/prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'clearsight'
    static_configs:
      - targets: ['localhost:8000']
EOF

# Restart services
sudo systemctl restart prometheus
sudo systemctl restart grafana-server
```

## Backup and Recovery

### 1. Automated Backups
Set up comprehensive backup strategy:

```bash
# Full backup script
cat > full_backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/clearsight"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U face_ai_prod_user -h localhost -d face_ai_prod \
    --no-password \
    --format=custom \
    --compress=9 \
    --file=$BACKUP_DIR/db_$DATE.dump

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /path/to/media/

# Static files backup (optional)
tar -czf $BACKUP_DIR/static_$DATE.tar.gz /path/to/staticfiles/

# Configuration backup
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    /path/to/env.production \
    /etc/nginx/sites-available/clearsight

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.dump" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

# Add to cron for daily backups
echo "0 3 * * * /path/to/full_backup.sh" | crontab -
```

### 2. Disaster Recovery Plan
Create a disaster recovery procedure:

1. **Regular Testing**: Test backup restoration monthly
2. **Off-site Storage**: Store backups in multiple locations
3. **Recovery Time Objective**: Define acceptable downtime
4. **Recovery Point Objective**: Define acceptable data loss
5. **Communication Plan**: Define incident response procedures

## Incident Response

### 1. Security Incident Procedure
```bash
# Security incident response script
cat > incident_response.sh << 'EOF'
#!/bin/bash
echo "SECURITY INCIDENT DETECTED - $(date)" >> /var/log/incidents.log

# Immediate actions
echo "1. Isolating affected systems..."
# Add commands to isolate systems

echo "2. Preserving evidence..."
# Add forensic commands

echo "3. Notifying security team..."
# Add notification commands

echo "4. Assessing damage..."
# Add assessment commands

echo "5. Restoring from backup..."
# Add recovery commands

echo "Incident response completed - $(date)" >> /var/log/incidents.log
EOF
```

### 2. Security Monitoring
Set up security monitoring:

```bash
# Install security monitoring tools
sudo apt install fail2ban rkhunter chkrootkit

# Configure fail2ban for Django
cat > /etc/fail2ban/jail.d/clearsight.conf << EOF
[clearsight]
enabled = true
port = http,https
filter = clearsight
logpath = /var/log/clearsight/security.log
maxretry = 3
bantime = 3600
EOF

# Create custom filter
cat > /etc/fail2ban/filter.d/clearsight.conf << EOF
[Definition]
failregex = ^.*SECURITY.*<HOST>.*$
ignoreregex =
EOF
```

### 3. Regular Security Audits
Schedule regular security assessments:

```bash
# Security audit script
cat > security_audit.sh << 'EOF'
#!/bin/bash
echo "=== Security Audit Report - $(date) ===" > audit_report.txt

echo "1. File Permissions Check:" >> audit_report.txt
find /path/to/app -type f -perm 777 >> audit_report.txt

echo "2. Running Processes:" >> audit_report.txt
ps aux | grep -E "(gunicorn|nginx|postgres|redis)" >> audit_report.txt

echo "3. Open Ports:" >> audit_report.txt
netstat -tlnp >> audit_report.txt

echo "4. Recent Logins:" >> audit_report.txt
last -10 >> audit_report.txt

echo "5. Disk Usage:" >> audit_report.txt
df -h >> audit_report.txt

echo "=== End of Security Audit ===" >> audit_report.txt

# Email report
mail -s "Security Audit Report" admin@your-domain.com < audit_report.txt
EOF

# Run weekly
echo "0 9 * * 1 /path/to/security_audit.sh" | crontab -
```

## Additional Security Measures

### 1. Web Application Firewall (WAF)
Consider implementing a WAF:

```bash
# Install ModSecurity for Nginx
sudo apt install libmodsecurity3 modsecurity-crs
sudo apt install nginx-mod-http-modsecurity

# Configure ModSecurity
sudo cp /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf
sudo sed -i 's/SecRuleEngine DetectionOnly/SecRuleEngine On/' /etc/modsecurity/modsecurity.conf
```

### 2. Intrusion Detection System
Set up IDS/IPS:

```bash
# Install Snort
sudo apt install snort

# Configure Snort for web application monitoring
# (Configuration details depend on your network setup)
```

### 3. Security Headers Check
Verify security headers are properly set:

```bash
# Security headers check script
curl -I https://your-domain.com | grep -E "(X-|Strict-Transport|Content-Security)"
```

This comprehensive security guide ensures your ClearSight Face AI deployment maintains the highest security standards in production environments.




