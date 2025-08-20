#!/bin/bash

# Face AI Django Application Docker Deployment Script
# This script deploys the Django application using Docker Compose

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
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

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install it and try again."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p media staticfiles temp_uploads logs/nginx ssl
    
    # Set proper permissions
    chmod 755 media staticfiles temp_uploads logs ssl
    
    print_success "Directories created successfully"
}

# Function to check environment file
check_environment() {
    if [ ! -f .env ]; then
        print_warning "Environment file (.env) not found. Creating from template..."
        if [ -f env.example ]; then
            cp env.example .env
            print_warning "Please edit .env file with your configuration values"
            print_warning "Then run this script again"
            exit 1
        else
            print_error "No environment template found. Please create .env file manually"
            exit 1
        fi
    fi
    
    # Source environment variables
    source .env
    
    # Check required variables
    if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "your-secret-key-here" ]; then
        print_error "Please set a proper SECRET_KEY in .env file"
        exit 1
    fi
    
    print_success "Environment configuration verified"
}

# Function to build and start services
deploy_services() {
    print_status "Building and starting services..."
    
    # Build images
    docker-compose build --no-cache
    
    # Start services
    docker-compose up -d
    
    print_success "Services started successfully"
}

# Function to wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for database
    print_status "Waiting for PostgreSQL..."
    until docker-compose exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
        sleep 2
    done
    print_success "PostgreSQL is ready"
    
    # Wait for Redis
    print_status "Waiting for Redis..."
    until docker-compose exec -T redis redis-cli ping; do
        sleep 2
    done
    print_success "Redis is ready"
    
    # Wait for Django
    print_status "Waiting for Django application..."
    until curl -f http://localhost:8000/health/ > /dev/null 2>&1; do
        sleep 5
    done
    print_success "Django application is ready"
}

# Function to run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    docker-compose exec web python manage.py migrate
    
    print_success "Database migrations completed"
}

# Function to create superuser
create_superuser() {
    print_status "Creating superuser..."
    
    read -p "Do you want to create a superuser? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose exec web python manage.py createsuperuser
    fi
}

# Function to show service status
show_status() {
    print_status "Service status:"
    docker-compose ps
    
    print_status "Container logs (last 10 lines):"
    docker-compose logs --tail=10
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy      Deploy the application (default)"
    echo "  start       Start the services"
    echo "  stop        Stop the services"
    echo "  restart     Restart the services"
    echo "  status      Show service status"
    echo "  logs        Show service logs"
    echo "  shell       Open shell in web container"
    echo "  migrate     Run database migrations"
    echo "  collectstatic Collect static files"
    echo "  clean       Clean up containers and volumes"
    echo "  help        Show this help message"
}

# Main deployment function
main_deploy() {
    print_status "Starting Face AI Django Application deployment..."
    
    check_docker
    check_docker_compose
    create_directories
    check_environment
    deploy_services
    wait_for_services
    run_migrations
    create_superuser
    show_status
    
    print_success "Deployment completed successfully!"
    print_status "Application is available at: http://localhost:8000"
    print_status "Nginx is available at: http://localhost:80"
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        main_deploy
        ;;
    "start")
        print_status "Starting services..."
        docker-compose up -d
        print_success "Services started"
        ;;
    "stop")
        print_status "Stopping services..."
        docker-compose down
        print_success "Services stopped"
        ;;
    "restart")
        print_status "Restarting services..."
        docker-compose restart
        print_success "Services restarted"
        ;;
    "status")
        show_status
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "shell")
        docker-compose exec web bash
        ;;
    "migrate")
        run_migrations
        ;;
    "collectstatic")
        print_status "Collecting static files..."
        docker-compose exec web python manage.py collectstatic --noinput
        print_success "Static files collected"
        ;;
    "clean")
        print_warning "This will remove all containers, images, and volumes. Are you sure? (y/n): "
        read -p "" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Cleaning up..."
            docker-compose down -v --rmi all
            docker system prune -f
            print_success "Cleanup completed"
        fi
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac
