#!/bin/bash

# Production Deployment Script for ClearSight Face AI
# This script sets up the application in production mode with security hardening

set -e  # Exit on any error

echo "🔒 Starting Production Deployment for ClearSight Face AI"
echo "======================================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to generate secure random string
generate_secret() {
    python3 -c "import secrets; print(secrets.token_urlsafe(64))"
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists python3; then
    echo "❌ Python3 is required but not installed. Aborting."
    exit 1
fi

if ! command_exists pip; then
    echo "❌ pip is required but not installed. Aborting."
    exit 1
fi

if ! command_exists psql; then
    echo "⚠️  PostgreSQL client not found. Make sure PostgreSQL is installed."
fi

echo "✅ Prerequisites check completed"

# Create production environment file
echo "🔧 Setting up production environment..."

if [ ! -f "env.production" ]; then
    echo "📝 Creating production environment file..."

    # Generate secure secrets
    SECRET_KEY=$(generate_secret)
    DB_PASSWORD=$(generate_secret)
    REDIS_PASSWORD=$(generate_secret)

    cat > env.production << EOF
# Production Environment Configuration
# Generated on $(date)

# Django Core Settings
DEBUG=False
SECRET_KEY=${SECRET_KEY}
DJANGO_SETTINGS_MODULE=backend.settings
ENVIRONMENT=production

# Server Configuration
ALLOWED_HOSTS=localhost,127.0.0.1
BASE_URL=http://localhost
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1

# Database Settings (PostgreSQL for production)
POSTGRES_DB=face_ai_prod
POSTGRES_USER=face_ai_prod_user
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis Settings (Production Redis)
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/1
REDIS_CACHE_URL=redis://:${REDIS_PASSWORD}@localhost:6379/2
REDIS_SESSION_URL=redis://:${REDIS_PASSWORD}@localhost:6379/3

# Security Settings
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
SECURE_REFERRER_POLICY=strict-origin-when-cross-origin

# Rate Limiting
RATELIMIT_ENABLE=True
LOGIN_RATELIMIT=5/m
API_RATELIMIT=100/h
SEARCH_RATELIMIT=30/m

# Service Configuration
MILVUS_HOST=localhost
MILVUS_PORT=19530
FACE_DETECTION_SERVICE_URL=http://localhost:5000/api/face-detection/
DATA_INGESTION_SERVICE_URL=http://localhost:8001

# File Upload Settings
MAX_UPLOAD_SIZE=104857600
MAX_VIDEO_FILE_SIZE=536870912
CHUNKED_UPLOAD_THRESHOLD=104857600

# Logging
LOG_LEVEL=INFO

# Admin Configuration (CHANGE THESE!)
ADMIN_EMAIL=admin@example.com
MANAGER_EMAIL=manager@example.com

# SSL Configuration (for HTTPS setup)
SSL_CERT_PATH=/etc/ssl/certs/localhost.crt
SSL_KEY_PATH=/etc/ssl/private/localhost.key

# Performance Settings
GUNICORN_WORKERS=2
GUNICORN_THREADS=2
GUNICORN_MAX_REQUESTS=1000
GUNICORN_TIMEOUT=30

EOF

    echo "✅ Production environment file created: env.production"
    echo "⚠️  IMPORTANT: Update the following in env.production:"
    echo "   - ALLOWED_HOSTS: Add your actual domain"
    echo "   - BASE_URL: Set your production domain"
    echo "   - CSRF_TRUSTED_ORIGINS: Add your production domains"
    echo "   - ADMIN_EMAIL and MANAGER_EMAIL: Set real email addresses"
    echo "   - Database credentials if using external DB"
    echo "   - SSL certificate paths for HTTPS"
else
    echo "✅ Production environment file already exists"
fi

# Set up Python virtual environment
echo "🐍 Setting up Python virtual environment..."

if [ ! -d "venv_prod" ]; then
    python3 -m venv venv_prod
    echo "✅ Virtual environment created: venv_prod"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source venv_prod/bin/activate
echo "✅ Virtual environment activated"

# Upgrade pip
pip install --upgrade pip

# Install production requirements
echo "📦 Installing production requirements..."

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Production requirements installed"
else
    echo "❌ requirements.txt not found"
    exit 1
fi

# Install additional security packages
echo "🔒 Installing security packages..."
pip install django-csp django-ratelimit django-helmet python-decouple sentry-sdk gunicorn psycopg2-binary redis

# Create logs directory
echo "📝 Setting up logging..."
mkdir -p logs
chmod 755 logs

# Set up database
echo "🗄️  Setting up database..."

# Load environment variables
if [ -f "env.production" ]; then
    export $(grep -v '^#' env.production | xargs)
fi

# Run Django migrations
echo "🔄 Running database migrations..."
python manage.py migrate --settings=backend.settings_production

# Create superuser (optional)
echo "👤 Creating superuser..."
echo "You will be prompted to create a superuser account."
echo "Press Ctrl+C to skip if you want to create it manually later."
python manage.py createsuperuser --settings=backend.settings_production || echo "Superuser creation skipped"

# Collect static files
echo "📄 Collecting static files..."
python manage.py collectstatic --noinput --settings=backend.settings_production

# Set proper permissions
echo "🔐 Setting secure permissions..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Set secure permissions on sensitive files
chmod 600 env.production
chmod 600 db.sqlite3 2>/dev/null || true
chmod 755 manage.py

# Create systemd service file (for Linux deployment)
echo "⚙️  Creating systemd service file..."
cat > clearsight.service << EOF
[Unit]
Description=ClearSight Face AI Application
After=network.target
Requires=redis-server.service postgresql.service

[Service]
Type=exec
User=${USER}
Group=${USER}
WorkingDirectory=${PWD}
Environment=PATH=${PWD}/venv_prod/bin
Environment=DJANGO_SETTINGS_MODULE=backend.settings_production
ExecStart=${PWD}/venv_prod/bin/gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 2
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
RestartSec=5
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd service file created: clearsight.service"

# Create nginx configuration
echo "🌐 Creating nginx configuration..."
cat > nginx.conf.production << EOF
# Nginx configuration for ClearSight Face AI (Production)

upstream clearsight_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name localhost;

    # Redirect HTTP to HTTPS (uncomment when SSL is set up)
    # return 301 https://\$server_name\$request_uri;

    # Serve static files
    location /static/ {
        alias ${PWD}/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Serve media files
    location /media/ {
        alias ${PWD}/media/;
        expires 30d;
        add_header Cache-Control "public";
    }

    # Main application
    location / {
        proxy_pass http://clearsight_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Security headers
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com;" always;

        # Timeout settings
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Health check endpoint
    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}

# HTTPS configuration (uncomment and configure when SSL certificates are available)
# server {
#     listen 443 ssl http2;
#     server_name your-domain.com;
#
#     ssl_certificate /etc/ssl/certs/your-domain.crt;
#     ssl_certificate_key /etc/ssl/private/your-domain.key;
#
#     ssl_protocols TLSv1.2 TLSv1.3;
#     ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
#     ssl_prefer_server_ciphers off;
#
#     # HSTS
#     add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
#
#     # SSL session cache
#     ssl_session_cache shared:SSL:10m;
#     ssl_session_timeout 10m;
#
#     location / {
#         proxy_pass http://clearsight_app;
#         # ... (same proxy settings as above)
#     }
# }
EOF

echo "✅ Nginx configuration created: nginx.conf.production"

# Create deployment checklist
echo "📋 Creating deployment checklist..."
cat > DEPLOYMENT_CHECKLIST.md << 'EOF'
# Production Deployment Checklist for ClearSight Face AI

## Pre-Deployment Tasks
- [ ] Update `ALLOWED_HOSTS` in `env.production` with your actual domain
- [ ] Update `BASE_URL` and `CSRF_TRUSTED_ORIGINS` with production URLs
- [ ] Set up SSL certificates and update certificate paths
- [ ] Configure email settings for notifications
- [ ] Set up PostgreSQL database and update credentials
- [ ] Configure Redis for caching and sessions
- [ ] Set up external services (Milvus, Face Detection Service)
- [ ] Configure firewall rules (allow 80, 443, 8000)

## Security Configuration
- [ ] Change SECRET_KEY to a strong random value
- [ ] Set DEBUG=False
- [ ] Enable HTTPS redirect
- [ ] Configure HSTS headers
- [ ] Set up proper database SSL connections
- [ ] Configure Redis authentication
- [ ] Set up monitoring and alerting

## Production Setup
- [ ] Install and configure PostgreSQL
- [ ] Install and configure Redis
- [ ] Install and configure Nginx
- [ ] Install and configure Gunicorn
- [ ] Set up SSL certificates
- [ ] Configure log rotation
- [ ] Set up backup procedures
- [ ] Configure monitoring (Prometheus/Grafana)

## Post-Deployment Verification
- [ ] Test application functionality
- [ ] Verify HTTPS is working
- [ ] Check security headers
- [ ] Test database connections
- [ ] Verify file uploads work
- [ ] Test user authentication
- [ ] Check logging is working
- [ ] Verify rate limiting
- [ ] Test error pages

## Maintenance Tasks
- [ ] Set up automated backups
- [ ] Configure log monitoring
- [ ] Set up health checks
- [ ] Configure alerts for downtime
- [ ] Plan for scaling and load balancing
- [ ] Set up CDN for static files
- [ ] Configure database replication

## Emergency Contacts
- Admin Email: [admin@example.com]
- Technical Support: [support@example.com]
- Hosting Provider: [provider details]

## Useful Commands
```bash
# Start application
sudo systemctl start clearsight

# Stop application
sudo systemctl stop clearsight

# View logs
sudo journalctl -u clearsight -f

# Restart application
sudo systemctl restart clearsight

# Check application status
sudo systemctl status clearsight
```
EOF

echo "✅ Deployment checklist created: DEPLOYMENT_CHECKLIST.md"

# Final security recommendations
echo ""
echo "🔒 SECURITY RECOMMENDATIONS:"
echo "=============================="
echo "1. 🔑 Change the SECRET_KEY in env.production to a new random value"
echo "2. 🛡️  Set up SSL/TLS certificates for HTTPS"
echo "3. 🗄️  Use PostgreSQL instead of SQLite for production"
echo "4. 🔐 Configure Redis with password authentication"
echo "5. 📧 Set up SMTP email for notifications"
echo "6. 🚨 Configure monitoring and alerting"
echo "7. 📊 Set up log aggregation and analysis"
echo "8. 🔄 Configure automated backups"
echo "9. 🚦 Set up rate limiting and DDoS protection"
echo "10. 🔍 Enable security scanning and vulnerability assessments"

echo ""
echo "🎉 Production deployment setup completed!"
echo "========================================="
echo "Next steps:"
echo "1. Review and update env.production with your settings"
echo "2. Follow the DEPLOYMENT_CHECKLIST.md"
echo "3. Test the deployment thoroughly"
echo "4. Set up monitoring and alerting"
echo ""
echo "🚀 To start the application in production mode:"
echo "   source venv_prod/bin/activate"
echo "   gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 2"
echo ""
echo "📝 Don't forget to:"
echo "   - Set ENVIRONMENT=production in your environment"
echo "   - Configure your web server (nginx/apache)"
echo "   - Set up SSL certificates"
echo "   - Configure firewall rules"




