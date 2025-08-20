#!/bin/bash

# Docker entrypoint script for Django Face AI application
# This script handles container initialization and startup

set -e

# Function to print colored output
print_info() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

print_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

# Function to wait for database
wait_for_db() {
    print_info "Waiting for database connection..."
    
    # Check if we're using PostgreSQL
    if [ "$DATABASE_ENGINE" = "postgresql" ] || [ -n "$POSTGRES_HOST" ]; then
        until python manage.py dbshell --database=default 2>/dev/null; do
            print_info "Database is unavailable - sleeping"
            sleep 2
        done
        print_success "Database is available"
    else
        print_info "Using SQLite database - no connection check needed"
    fi
}

# Function to wait for Redis
wait_for_redis() {
    print_info "Waiting for Redis connection..."
    
    if [ -n "$REDIS_URL" ] || [ -n "$CELERY_BROKER_URL" ]; then
        until python -c "
import redis
try:
    r = redis.from_url('${REDIS_URL:-${CELERY_BROKER_URL}}')
    r.ping()
    print('Redis is available')
except:
    exit(1)
" 2>/dev/null; do
            print_info "Redis is unavailable - sleeping"
            sleep 2
        done
        print_success "Redis is available"
    else
        print_info "Redis not configured - skipping connection check"
    fi
}

# Function to run database migrations
run_migrations() {
    print_info "Running database migrations..."
    python manage.py migrate --noinput
    print_success "Database migrations completed"
}

# Function to collect static files
collect_static() {
    print_info "Collecting static files..."
    python manage.py collectstatic --noinput
    print_success "Static files collected"
}

# Function to create superuser if needed
create_superuser() {
    if [ "$CREATE_SUPERUSER" = "true" ] && [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
        print_info "Creating superuser..."
        python manage.py createsuperuser --noinput || print_warning "Superuser creation failed or user already exists"
    fi
}

# Function to check if this is the first run
is_first_run() {
    if [ ! -f "/app/.first_run_complete" ]; then
        return 0  # First run
    else
        return 1  # Not first run
    fi
}

# Function to mark first run as complete
mark_first_run_complete() {
    touch /app/.first_run_complete
}

# Main initialization function
initialize_app() {
    print_info "Initializing Django Face AI application..."
    
    # Wait for dependencies
    wait_for_db
    wait_for_redis
    
    # Run migrations
    run_migrations
    
    # Collect static files
    collect_static
    
    # Create superuser if needed
    create_superuser
    
    # Mark first run as complete
    mark_first_run_complete
    
    print_success "Application initialization completed"
}

# Function to start the application
start_app() {
    print_info "Starting Django application..."
    
    # Check if we should run in development or production mode
    if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ]; then
        print_info "Starting in development mode..."
        exec python manage.py runserver 0.0.0.0:8000
    else
        print_info "Starting in production mode..."
        exec gunicorn \
            --bind 0.0.0.0:8000 \
            --workers ${GUNICORN_WORKERS:-4} \
            --worker-class ${GUNICORN_WORKER_CLASS:-sync} \
            --worker-connections ${GUNICORN_WORKER_CONNECTIONS:-1000} \
            --max-requests ${GUNICORN_MAX_REQUESTS:-1000} \
            --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-100} \
            --timeout ${GUNICORN_TIMEOUT:-120} \
            --keep-alive ${GUNICORN_KEEP_ALIVE:-2} \
            --access-logfile - \
            --error-logfile - \
            backend.wsgi:application
    fi
}

# Main script logic
main() {
    print_info "Django Face AI container starting..."
    
    # Change to app directory
    cd /app
    
    # Initialize application on first run
    if is_first_run; then
        initialize_app
    else
        print_info "Application already initialized, skipping setup"
    fi
    
    # Start the application
    start_app
}

# Handle signals gracefully
trap 'print_info "Received signal, shutting down..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"
