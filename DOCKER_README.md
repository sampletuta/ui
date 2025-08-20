# Face AI Django Application - Docker Deployment

This document provides comprehensive instructions for deploying the Face AI Django application using Docker.

## Overview

The application is containerized using Docker and Docker Compose, providing a scalable and portable deployment solution. The setup includes:

- **Django Web Application** - Main application server
- **PostgreSQL Database** - Primary database
- **Redis** - Caching and session storage
- **Nginx** - Reverse proxy and static file serving
- **Celery** - Background task processing
- **Celery Beat** - Scheduled task management

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available
- At least 10GB disk space

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd ui

# Copy environment template
cp env.example .env

# Edit environment variables
nano .env
```

### 2. Configure Environment

Edit the `.env` file with your configuration:

```bash
# Django Settings
DEBUG=False
SECRET_KEY=your-secure-secret-key-here
DJANGO_SETTINGS_MODULE=backend.settings_docker

# Database Settings
POSTGRES_DB=face_ai_db
POSTGRES_USER=face_ai_user
POSTGRES_PASSWORD=your-secure-password

# Milvus Settings (External Service)
MILVUS_HOST=your-milvus-host
MILVUS_PORT=19530

# Other settings...
```

### 3. Deploy

```bash
# Make deployment script executable
chmod +x deploy.sh

# Deploy the application
./deploy.sh
```

## Manual Deployment

If you prefer manual deployment:

```bash
# Create necessary directories
mkdir -p media staticfiles temp_uploads logs/nginx ssl

# Build and start services
docker-compose build
docker-compose up -d

# Wait for services to be ready, then run migrations
docker-compose exec web python manage.py migrate

# Create superuser (optional)
docker-compose exec web python manage.py createsuperuser
```

## Service Management

### Using the Deployment Script

```bash
# Start services
./deploy.sh start

# Stop services
./deploy.sh stop

# Restart services
./deploy.sh restart

# View status
./deploy.sh status

# View logs
./deploy.sh logs

# Open shell in web container
./deploy.sh shell

# Run migrations
./deploy.sh migrate

# Collect static files
./deploy.sh collectstatic

# Clean up everything
./deploy.sh clean
```

### Using Docker Compose Directly

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Execute commands
docker-compose exec web python manage.py shell
docker-compose exec db psql -U face_ai_user -d face_ai_db
```

## Production Deployment

For production deployment, use the production configuration:

```bash
# Use production docker-compose file
docker-compose -f docker-compose.prod.yml up -d

# Or use the production Dockerfile
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### Production Considerations

1. **Environment Variables**: Set all required environment variables
2. **SSL Certificates**: Configure SSL in Nginx for HTTPS
3. **Resource Limits**: Adjust resource limits in docker-compose.prod.yml
4. **Monitoring**: Set up monitoring and logging
5. **Backup**: Configure database and media backups

## Configuration Files

### Docker Compose Files

- `docker-compose.yml` - Development configuration
- `docker-compose.prod.yml` - Production configuration

### Django Settings

- `backend/settings.py` - Base settings
- `backend/settings_docker.py` - Docker-specific overrides

### Nginx Configuration

- `nginx.conf` - Development Nginx configuration
- `nginx.prod.conf` - Production Nginx configuration (create as needed)

## Service Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Nginx     │    │   Django    │    │ PostgreSQL │
│  (Port 80)  │◄──►│  (Port 8000)│◄──►│  (Port 5432)│
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   ▼                   │
       │            ┌─────────────┐            │
       │            │    Redis    │            │
       │            │  (Port 6379)│            │
       │            └─────────────┘            │
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Static    │    │   Celery    │    │   Celery    │
│   Files     │    │   Worker    │    │    Beat     │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Environment Variables

### Required Variables

- `SECRET_KEY` - Django secret key
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password

### Optional Variables

- `DEBUG` - Debug mode (default: False)
- `MILVUS_HOST` - Milvus host (default: localhost)
- `MILVUS_PORT` - Milvus port (default: 19530)
- `REDIS_URL` - Redis connection URL
- `FACE_AI_MAX_WORKERS` - Face AI worker count

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check what's using the ports
   sudo netstat -tlnp | grep :8000
   sudo netstat -tlnp | grep :80
   ```

2. **Permission Issues**
   ```bash
   # Fix directory permissions
   sudo chown -R $USER:$USER media staticfiles temp_uploads logs
   chmod 755 media staticfiles temp_uploads logs
   ```

3. **Database Connection Issues**
   ```bash
   # Check database container
   docker-compose logs db
   docker-compose exec db pg_isready -U face_ai_user
   ```

4. **Static Files Not Loading**
   ```bash
   # Recollect static files
   docker-compose exec web python manage.py collectstatic --noinput
   ```

### Logs and Debugging

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs web
docker-compose logs db
docker-compose logs nginx

# Follow logs in real-time
docker-compose logs -f web

# Check container status
docker-compose ps
docker stats
```

## Performance Tuning

### Resource Allocation

Adjust resource limits in docker-compose files:

```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '2.0'
    reservations:
      memory: 1G
      cpus: '1.0'
```

### Gunicorn Configuration

Modify worker settings in Dockerfile.prod:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "gevent", "backend.wsgi:application"]
```

### Database Optimization

- Enable connection pooling
- Configure appropriate memory settings
- Use SSD storage for production

## Security Considerations

1. **Environment Variables**: Never commit `.env` files
2. **Network Security**: Use internal Docker networks
3. **User Permissions**: Run containers as non-root users
4. **SSL/TLS**: Enable HTTPS in production
5. **Firewall**: Restrict external access to necessary ports only

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec db pg_dump -U face_ai_user face_ai_db > backup.sql

# Restore backup
docker-compose exec -T db psql -U face_ai_user -d face_ai_db < backup.sql
```

### Media Files Backup

```bash
# Backup media directory
tar -czf media_backup.tar.gz media/

# Restore media directory
tar -xzf media_backup.tar.gz
```

## Monitoring and Health Checks

The application includes health check endpoints:

- **Application Health**: `http://localhost:8000/health/`
- **Database Health**: Built into Docker Compose
- **Redis Health**: Built into Docker Compose

## Support and Maintenance

### Regular Maintenance

1. **Update Dependencies**: Regularly update Docker images
2. **Log Rotation**: Configure log rotation for production
3. **Security Updates**: Keep base images updated
4. **Performance Monitoring**: Monitor resource usage

### Scaling

To scale the application:

```bash
# Scale web workers
docker-compose up -d --scale web=3

# Scale Celery workers
docker-compose up -d --scale celery=2
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Nginx Configuration](https://nginx.org/en/docs/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
- [Redis Docker](https://hub.docker.com/_/redis)
