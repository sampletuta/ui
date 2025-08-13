#!/bin/bash

# Deployment script for Surveillance System

echo "🚀 Starting deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your production settings before continuing."
    echo "   You can run this script again after editing .env"
    exit 0
fi

# Build and start the services
echo "🔨 Building Docker images..."
docker compose build

echo "🚀 Starting services..."
docker compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run migrations
echo "🗄️  Running database migrations..."
docker compose exec web python manage.py migrate

# Create superuser if needed
echo "👤 Creating superuser..."
docker compose exec web python manage.py createsuperuser --noinput || echo "Superuser creation skipped (may already exist)"

# Collect static files
echo "📦 Collecting static files..."
docker compose exec web python manage.py collectstatic --noinput

echo "✅ Deployment completed!"
echo "🌐 Application is running at http://localhost:8000"
echo "📊 To view logs: docker compose logs -f"
echo "🛑 To stop: docker compose down"
