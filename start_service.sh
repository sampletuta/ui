#!/bin/bash

# ClearSight Face AI - Production Service Startup Script
# This script starts the entire ClearSight Face AI application with all necessary configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}[HEADER]${NC} $1"
}

print_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to wait for a service to be ready
wait_for_service() {
    local port=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1

    print_info "Waiting for $service_name to be ready on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if port_in_use $port; then
            print_success "$service_name is ready on port $port"
            return 0
        fi
        
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start on port $port after $max_attempts seconds"
    return 1
}

# Function to stop existing services
stop_existing_services() {
    print_step "Stopping existing services..."
    
    # Stop Django development server
    if pgrep -f "python.*manage.py.*runserver" > /dev/null; then
        print_info "Stopping existing Django development server..."
        pkill -f "python.*manage.py.*runserver" || true
        sleep 2
    fi
    
    # Stop any other Python processes that might be running the app
    if pgrep -f "python.*backend" > /dev/null; then
        print_info "Stopping existing Python backend processes..."
        pkill -f "python.*backend" || true
        sleep 2
    fi
    
    print_success "Existing services stopped"
}

# Function to check system requirements
check_requirements() {
    print_step "Checking system requirements..."
    
    # Check if Python 3 is installed
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_info "Python version: $python_version"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found. Please run 'python3 -m venv venv' first."
        exit 1
    fi
    
    # Check if required directories exist
    required_dirs=("backendapp" "face_ai" "backend" "logs" "temp" "temp_uploads")
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            print_warning "Directory $dir not found, creating it..."
            mkdir -p "$dir"
        fi
    done
    
    print_success "System requirements check completed"
}

# Function to setup environment
setup_environment() {
    print_step "Setting up environment..."
    
    # Activate virtual environment
    print_info "Activating virtual environment..."
    source venv/bin/activate
    
    # Load environment variables from env file
    ENV_FILE=""
    if [ -n "${ENVIRONMENT:-}" ] && [ "$ENVIRONMENT" = "production" ] && [ -f "env.production" ]; then
        ENV_FILE="env.production"
    elif [ -f "env.production" ] && grep -qi "^ENVIRONMENT=production" env.production; then
        ENV_FILE="env.production"
    elif [ -f "env" ]; then
        ENV_FILE="env"
    fi

    if [ -n "$ENV_FILE" ]; then
        print_info "Loading environment from $ENV_FILE"
        set -a
        . "./$ENV_FILE"
        set +a
    else
        print_warning "No env file found; using development defaults"
    fi

    # Ensure sensible defaults if not provided
    export ENVIRONMENT="${ENVIRONMENT:-development}"
    if [ -z "${DEBUG:-}" ]; then
        if [ "$ENVIRONMENT" = "production" ]; then
            export DEBUG=True
        else
            export DEBUG=True
        fi
    fi

    # Always set PYTHONPATH
    export PYTHONPATH="$(pwd)"
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p temp
    mkdir -p temp_uploads
    mkdir -p staticfiles
    
    print_success "Environment setup completed"
}

# Function to install dependencies
install_dependencies() {
    print_step "Installing dependencies..."
    
    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi
    
    # Install Python dependencies
    print_info "Installing Python dependencies..."
    pip install -q -r requirements.txt
    
    print_success "Dependencies installed"
}

# Function to setup database
setup_database() {
    print_step "Setting up database..."
    
    # Run database migrations
    print_info "Running database migrations..."
    python manage.py migrate --noinput
    
    # Create superuser if it doesn't exist
    print_info "Checking for superuser..."
    if ! python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(email='admin@admin.com').exists()" 2>/dev/null | grep -q "True"; then
        print_info "Creating default superuser..."
        python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@admin.com').exists():
    User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
    print('Superuser created: admin@admin.com / admin123')
else:
    print('Superuser already exists')
"
    else
        print_info "Superuser already exists"
    fi
    
    print_success "Database setup completed"
}

# Function to collect static files
collect_static_files() {
    print_step "Collecting static files..."
    
    # Create favicon.ico if it doesn't exist
    if [ ! -f "backendapp/static/img/favicon.ico" ]; then
        print_info "Creating favicon.ico..."
        mkdir -p backendapp/static/img
        if [ -f "backendapp/static/img/user.jpg" ]; then
            cp backendapp/static/img/user.jpg backendapp/static/img/favicon.ico
        else
            # Create a simple favicon
            echo "Creating placeholder favicon..."
            touch backendapp/static/img/favicon.ico
        fi
    fi
    
    # Collect static files
    print_info "Collecting static files..."
    python manage.py collectstatic --noinput
    
    print_success "Static files collected"
}

# Function to start the service
start_service() {
    print_step "Starting ClearSight Face AI service..."
    
    # Check if port 8000 is available
    if port_in_use 8000; then
        print_warning "Port 8000 is already in use. Attempting to free it..."
        stop_existing_services
        sleep 3
    fi
    
    # Start Django development server
    print_info "Starting Django development server on http://0.0.0.0:8000..."
    print_info "Environment: $ENVIRONMENT"
    print_info "Debug Mode: $DEBUG"
    
    # Start the server in background (env already loaded; avoid passing secrets on cmdline)
    nohup python manage.py runserver 0.0.0.0:8000 > logs/django.log 2>&1 &
    DJANGO_PID=$!
    
    # Wait for the service to be ready
    if wait_for_service 8000 "Django Server"; then
        print_success "ClearSight Face AI service started successfully!"
        print_success "PID: $DJANGO_PID"
        echo $DJANGO_PID > logs/django.pid
        
        # Display service information
        print_header "=== SERVICE INFORMATION ==="
        print_info "Service URL: http://localhost:8000"
        print_info "Login URL: http://localhost:8000/login/"
        print_info "Admin URL: http://localhost:8000/admin/"
        print_info "Default Login: admin@admin.com / admin123"
        print_info "Log File: logs/django.log"
        print_info "PID File: logs/django.pid"
        print_header "=========================="
        
        # Test the service
        print_info "Testing service..."
        sleep 2
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login/ | grep -q "200\|302"; then
            print_success "Service is responding correctly!"
        else
            print_warning "Service may not be fully ready yet. Please wait a moment and try accessing http://localhost:8000"
        fi
        
        return 0
    else
        print_error "Failed to start the service"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -s, --stop     Stop the running service"
    echo "  -r, --restart  Restart the service"
    echo "  -l, --logs     Show service logs"
    echo "  -t, --test     Test the service"
    echo "  -c, --clean    Clean up and restart"
    echo ""
    echo "Examples:"
    echo "  $0              # Start the service"
    echo "  $0 --stop       # Stop the service"
    echo "  $0 --restart    # Restart the service"
    echo "  $0 --logs       # Show logs"
    echo "  $0 --test       # Test the service"
}

# Function to stop the service
stop_service() {
    print_step "Stopping ClearSight Face AI service..."
    
    if [ -f "logs/django.pid" ]; then
        PID=$(cat logs/django.pid)
        if kill -0 $PID 2>/dev/null; then
            print_info "Stopping Django server (PID: $PID)..."
            kill $PID
            rm -f logs/django.pid
            print_success "Service stopped"
        else
            print_warning "Service was not running"
            rm -f logs/django.pid
        fi
    else
        print_info "No PID file found, stopping any running Django processes..."
        pkill -f "python.*manage.py.*runserver" || true
    fi
}

# Function to show logs
show_logs() {
    if [ -f "logs/django.log" ]; then
        print_info "Showing service logs (last 50 lines):"
        echo "----------------------------------------"
        tail -50 logs/django.log
    else
        print_warning "No log file found"
    fi
}

# Function to test the service
test_service() {
    print_step "Testing ClearSight Face AI service..."
    
    if port_in_use 8000; then
        print_info "Testing service endpoints..."
        
        # Test login page
        response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login/)
        if [ "$response" = "200" ] || [ "$response" = "302" ]; then
            print_success "Login page: OK ($response)"
        else
            print_error "Login page: FAILED ($response)"
        fi
        
        # Test root page
        response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
        if [ "$response" = "200" ] || [ "$response" = "302" ] || [ "$response" = "403" ]; then
            print_success "Root page: OK ($response)"
        else
            print_error "Root page: FAILED ($response)"
        fi
        
        print_info "Service URL: http://localhost:8000"
        print_info "Login URL: http://localhost:8000/login/"
    else
        print_error "Service is not running on port 8000"
    fi
}

# Function to clean and restart
clean_restart() {
    print_step "Cleaning and restarting service..."
    
    stop_service
    sleep 2
    
    # Clean up
    print_info "Cleaning up..."
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Restart
    start_service
}

# Main function
main() {
    print_header "ClearSight Face AI - Service Startup Script"
    print_header "============================================="
    
    # Parse command line arguments
    case "${1:-}" in
        -h|--help)
            show_usage
            exit 0
            ;;
        -s|--stop)
            stop_service
            exit 0
            ;;
        -r|--restart)
            stop_service
            sleep 2
            main
            ;;
        -l|--logs)
            show_logs
            exit 0
            ;;
        -t|--test)
            test_service
            exit 0
            ;;
        -c|--clean)
            clean_restart
            exit 0
            ;;
        "")
            # Default: start the service
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
    
    # Main startup sequence
    stop_existing_services
    check_requirements
    setup_environment
    install_dependencies
    setup_database
    collect_static_files
    start_service
    
    print_header "============================================="
    print_success "ClearSight Face AI service is now running!"
    print_info "Access your application at: http://localhost:8000"
    print_info "Use '$0 --help' for more options"
    print_header "============================================="
}

# Run main function
main "$@"




