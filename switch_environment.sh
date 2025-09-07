#!/bin/bash

# Environment Switcher for ClearSight Face AI
# Switches between development and production modes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if environment argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 {dev|prod|status}"
    echo "  dev    - Switch to development mode"
    echo "  prod   - Switch to production mode"
    echo "  status - Show current environment status"
    exit 1
fi

ACTION=$1

case $ACTION in
    "status")
        print_info "Checking current environment status..."

        if [ -f ".env" ]; then
            if grep -q "ENVIRONMENT=production" .env 2>/dev/null; then
                print_status "Current environment: PRODUCTION"
            else
                print_status "Current environment: DEVELOPMENT"
            fi
        else
            print_warning "No .env file found"
        fi

        # Check Django settings
        if [ -n "$DJANGO_SETTINGS_MODULE" ]; then
            print_info "Django settings module: $DJANGO_SETTINGS_MODULE"
        fi

        if [ -n "$ENVIRONMENT" ]; then
            print_info "Environment variable: $ENVIRONMENT"
        fi

        # Check if DEBUG is set
        if [ -n "$DEBUG" ]; then
            if [ "$DEBUG" = "True" ]; then
                print_warning "DEBUG is enabled"
            else
                print_status "DEBUG is disabled (Production mode)"
            fi
        fi

        exit 0
        ;;

    "dev")
        print_info "Switching to DEVELOPMENT mode..."

        # Create or update .env file for development
        cat > .env << EOF
# Development Environment
DEBUG=True
ENVIRONMENT=development
DJANGO_SETTINGS_MODULE=backend.settings

# Database (SQLite for development)
DATABASE_URL=sqlite:///db.sqlite3

# Redis (Local)
REDIS_URL=redis://localhost:6379/0

# Services
MILVUS_HOST=localhost
MILVUS_PORT=19530
FACE_DETECTION_SERVICE_URL=http://localhost:5000/api/face-detection/
DATA_INGESTION_SERVICE_URL=http://localhost:8001

# Security (relaxed for development)
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_SSL_REDIRECT=False

# Development specific
SECRET_KEY=dev-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.86.65
EOF

        print_status "✅ Development environment configured"
        print_warning "⚠️  Remember to:"
        print_warning "   - Use strong SECRET_KEY in production"
        print_warning "   - Enable SSL/TLS"
        print_warning "   - Set up proper database"
        print_warning "   - Configure security headers"
        ;;

    "prod")
        print_info "Switching to PRODUCTION mode..."

        if [ ! -f "env.example" ]; then
            print_error "Template environment file (env.example) not found!"
            exit 1
        fi

        # Copy template and configure for production
        cp env.example .env

        # Add production-specific settings
        cat >> .env << EOF

# Production mode confirmation
ENVIRONMENT=production
DJANGO_SETTINGS_MODULE=backend.settings_production

# Security confirmations
DEBUG=False
EOF

        print_status "✅ Production environment configured"
        print_warning "🔒 SECURITY CHECKLIST:"
        print_warning "   □ Update SECRET_KEY with strong random value"
        print_warning "   □ Set ALLOWED_HOSTS to your actual domain"
        print_warning "   □ Configure SSL/TLS certificates"
        print_warning "   □ Set up PostgreSQL database"
        print_warning "   □ Configure Redis with authentication"
        print_warning "   □ Enable HTTPS redirect"
        print_warning "   □ Set up monitoring and logging"
        print_warning "   □ Configure firewall rules"
        print_warning "   □ Set up automated backups"
        ;;

    *)
        print_error "Invalid action: $ACTION"
        echo "Usage: $0 {dev|prod|status}"
        exit 1
        ;;
esac

print_info ""
print_info "Environment switch completed!"
print_info "To apply changes, restart your application:"
print_info "  source venv/bin/activate  # or venv_prod/bin/activate"
print_info "  python manage.py runserver  # or gunicorn command"
print_info ""
print_info "Or reload your web server if using production setup"




