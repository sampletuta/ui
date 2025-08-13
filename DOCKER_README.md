# Docker Deployment Guide

This guide will help you deploy the Surveillance System using Docker and Docker Compose.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

## Quick Start

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd ui
   ```

2. **Run the deployment script**:
   ```bash
   ./deploy.sh
   ```

3. **Access the application**:
   - Open your browser and go to `http://localhost:8000`
   - The application will be running with PostgreSQL database

## Manual Deployment

If you prefer to deploy manually:

1. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your production settings
   ```

2. **Build and start services**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Run database migrations**:
   ```bash
   docker-compose exec web python manage.py migrate
   ```

4. **Create a superuser**:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

## Environment Variables

Edit the `.env` file to configure your deployment:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Auto-generated |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `POSTGRES_DB` | Database name | `surveillance_db` |
| `POSTGRES_USER` | Database user | `surveillance_user` |
| `POSTGRES_PASSWORD` | Database password | `surveillance_password` |
| `POSTGRES_HOST` | Database host | `db` |
| `POSTGRES_PORT` | Database port | `5432` |

## Services

The Docker Compose setup includes:

- **Web Application**: Django application running on port 8000
- **PostgreSQL Database**: Persistent database for data storage
- **Volumes**: Persistent storage for media files, static files, and database

## Useful Commands

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Access Django shell
docker-compose exec web python manage.py shell

# Run Django commands
docker-compose exec web python manage.py [command]

# Backup database
docker-compose exec db pg_dump -U surveillance_user surveillance_db > backup.sql

# Restore database
docker-compose exec -T db psql -U surveillance_user surveillance_db < backup.sql
```

## Production Considerations

1. **Security**:
   - Change default passwords in `.env`
   - Use strong SECRET_KEY
   - Set DEBUG=False
   - Configure ALLOWED_HOSTS properly

2. **Performance**:
   - Adjust Gunicorn workers based on CPU cores
   - Configure PostgreSQL connection pooling
   - Use CDN for static files in production

3. **Monitoring**:
   - Set up log aggregation
   - Monitor container health
   - Configure backups

## Troubleshooting

### Common Issues

1. **Port already in use**:
   ```bash
   # Check what's using port 8000
   sudo lsof -i :8000
   # Change port in docker-compose.yml
   ```

2. **Database connection issues**:
   ```bash
   # Check database logs
   docker-compose logs db
   # Restart database
   docker-compose restart db
   ```

3. **Permission issues**:
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

### Logs

View specific service logs:
```bash
docker-compose logs web    # Application logs
docker-compose logs db     # Database logs
```

## Development

For development with Docker:

```bash
# Start services in development mode
DEBUG=True docker-compose up

# Run tests
docker-compose exec web python manage.py test

# Install new dependencies
docker-compose exec web pip install package_name
# Then update requirements.txt
```

## File Structure

```
ui/
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Multi-service orchestration
├── requirements.txt        # Python dependencies
├── .dockerignore          # Files to exclude from Docker build
├── deploy.sh              # Automated deployment script
├── env.example            # Environment variables template
└── DOCKER_README.md       # This file
```

