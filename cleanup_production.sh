#!/bin/bash

# Production Cleanup Script for ClearSight Face AI
# Removes development files, caches, and unnecessary content

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_info "🧹 Starting Production Cleanup for ClearSight Face AI"
echo "=================================================="

# Create backup of important files before cleanup
print_info "📦 Creating backup of important files..."

BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup critical configuration files
cp env.production "$BACKUP_DIR/" 2>/dev/null || true
cp requirements.txt "$BACKUP_DIR/" 2>/dev/null || true
cp nginx.conf.production "$BACKUP_DIR/" 2>/dev/null || true
cp clearsight.service "$BACKUP_DIR/" 2>/dev/null || true

print_success "Backup created in: $BACKUP_DIR"

# Remove debug and test files
print_info "🧪 Removing debug and test files..."

DEBUG_FILES=(
    "debug_face_detection.py"
    "diagnose_face_detection.py"
    "test_face_detection_fix.py"
    "test_yunet_onnx.py"
    "backendapp/tests.py"
    "face_ai/run_asgi.py"
    "face_ai/ASGI_README.md"
)

for file in "${DEBUG_FILES[@]}"; do
    if [ -f "$file" ]; then
        rm -f "$file"
        print_success "Removed: $file"
    fi
done

# Remove development scripts
print_info "🛠️  Removing development scripts..."

DEV_SCRIPTS=(
    "cleanup.sh"
    "init.sql"
    "deploy.sh"
)

for script in "${DEV_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        rm -f "$script"
        print_success "Removed: $script"
    fi
done

# Remove development SQLite database
print_info "🗄️  Removing development database..."
if [ -f "db.sqlite3" ]; then
    rm -f "db.sqlite3"
    print_success "Removed: db.sqlite3"
fi

# Remove temporary uploads directory
print_info "📁 Removing temporary files..."
if [ -d "temp_uploads" ]; then
    rm -rf "temp_uploads"
    print_success "Removed: temp_uploads/"
fi

# Remove logs directory (will be recreated in production)
if [ -d "logs" ]; then
    rm -rf "logs"
    print_success "Removed: logs/"
fi

# Remove __pycache__ directories
print_info "🗂️  Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Remove development configuration files
print_info "⚙️  Cleaning configuration files..."

DEV_CONFIGS=(
    "env.development"
    "backend/settings_docker.py"
    "docker-compose.yml"
    "Dockerfile"
    "docker-entrypoint.sh"
)

for config in "${DEV_CONFIGS[@]}"; do
    if [ -f "$config" ]; then
        rm -f "$config"
        print_success "Removed: $config"
    fi
done

# Remove duplicate face detection model (keep one in face_ai/)
if [ -f "face_detection_yunet_2023mar.onnx" ] && [ -f "face_ai/face_detection_yunet_2023mar.onnx" ]; then
    rm -f "face_detection_yunet_2023mar.onnx"
    print_success "Removed duplicate: face_detection_yunet_2023mar.onnx"
fi

# Remove unnecessary README and documentation files
print_info "📚 Cleaning documentation files..."

DOC_FILES=(
    "plan_report.md"
    "backendapp/views/README.md"
    "face_ai/AUTOMATION_SUMMARY.md"
    "face_ai/CONFIGURATION.md"
    "face_ai/MIGRATION_SUMMARY.md"
    "face_ai/FACE_VERIFICATION_README.md"
    "face_ai/README.md"
    "video_player/API_README.md"
    "video_player/STREAMING_PLAYER_README.md"
)

for doc in "${DOC_FILES[@]}"; do
    if [ -f "$doc" ]; then
        rm -f "$doc"
        print_success "Removed: $doc"
    fi
done

# Clean up requirements files - keep only production ones
print_info "📦 Cleaning requirements files..."
if [ -f "grequirements.txt" ]; then
    rm -f "grequirements.txt"
    print_success "Removed: grequirements.txt"
fi

# Remove table.html template (it's a demo template)
if [ -f "backendapp/templates/table.html" ]; then
    rm -f "backendapp/templates/table.html"
    print_success "Removed demo template: backendapp/templates/table.html"
fi

# Remove video_player 404.html (duplicate with main one)
if [ -f "video_player/templates/404.html" ]; then
    rm -f "video_player/templates/404.html"
    print_success "Removed duplicate: video_player/templates/404.html"
fi

# Clean up management commands - remove development ones
print_info "🛠️  Cleaning management commands..."

# Keep only essential management commands
find . -path "./backendapp/management/commands/*" -name "*.py" | while read -r cmd_file; do
    filename=$(basename "$cmd_file")
    if [[ "$filename" != "populate_watchlist.py" && "$filename" != "__init__.py" ]]; then
        rm -f "$cmd_file"
        print_success "Removed management command: $cmd_file"
    fi
done

# Keep only essential face_ai management commands
find . -path "./face_ai/management/commands/*" -name "*.py" | while read -r cmd_file; do
    filename=$(basename "$cmd_file")
    if [[ "$filename" == "__init__.py" ]]; then
        continue
    fi
    # Remove development/debug commands
    if [[ "$filename" == *"debug"* || "$filename" == *"test"* || "$filename" == *"dev"* ]]; then
        rm -f "$cmd_file"
        print_success "Removed face_ai management command: $cmd_file"
    fi
done

# Clean up empty directories
print_info "📁 Removing empty directories..."
find . -type d -empty -delete 2>/dev/null || true

# Create production .gitignore
print_info "📝 Creating production .gitignore..."
cat > .gitignore.production << 'EOF'
# Production .gitignore for ClearSight Face AI

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
staticfiles/
media/
temp_uploads/

# Environment variables
.env
.env.local
.env.production.local
env.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
logs/
*.log
django.log
security.log
access.log
error.log

# Backups (keep in separate location)
backup_*/

# Temporary files
*.tmp
*.temp
.cache/
.pytest_cache/
.coverage
htmlcov/

# Node.js (if any)
node_modules/
npm-debug.log*

# SSL certificates (don't commit private keys)
*.key
*.pem
!*.pub

# Database dumps
*.dump
*.sql
!init.sql.template
EOF

print_success "Created production .gitignore"

# Create production directory structure
print_info "📂 Creating production directory structure..."

# Create logs directory
mkdir -p logs
chmod 755 logs

# Create media directory
mkdir -p media
chmod 755 media

# Create temp directory for file uploads
mkdir -p temp
chmod 755 temp

# Set proper permissions
print_info "🔐 Setting production permissions..."

# Make scripts executable
chmod +x *.sh 2>/dev/null || true
chmod +x deploy_production.sh 2>/dev/null || true
chmod +x switch_environment.sh 2>/dev/null || true

# Set restrictive permissions on sensitive files
chmod 600 env.production 2>/dev/null || true
chmod 600 backend/settings_production.py 2>/dev/null || true

# Make manage.py executable
chmod +x manage.py

print_success "Production permissions set"

# Final cleanup summary
print_info ""
print_info "🧹 CLEANUP SUMMARY"
echo "=================="

echo "✅ Removed debug/test files"
echo "✅ Removed development scripts"
echo "✅ Removed SQLite database"
echo "✅ Removed temporary directories"
echo "✅ Removed Python cache files"
echo "✅ Removed development configurations"
echo "✅ Removed duplicate files"
echo "✅ Removed unnecessary documentation"
echo "✅ Cleaned management commands"
echo "✅ Created production .gitignore"
echo "✅ Set production permissions"
echo "✅ Created production directory structure"

print_info ""
print_info "📦 BACKUP LOCATION: $BACKUP_DIR"
print_warning "⚠️  IMPORTANT: Review the backup before deleting!"
print_info ""
print_info "🎯 PRODUCTION READY CHECKLIST:"
echo "=============================="
echo "□ Update env.production with your actual values"
echo "□ Set SECRET_KEY to a strong random value"
echo "□ Configure ALLOWED_HOSTS for your domain"
echo "□ Set up SSL certificates"
echo "□ Configure PostgreSQL database"
echo "□ Set up Redis with authentication"
echo "□ Configure nginx with SSL"
echo "□ Test the application thoroughly"
echo "□ Set up monitoring and logging"
echo "□ Configure automated backups"
echo ""
print_success "🧹 Production cleanup completed successfully!"
print_info "🚀 Your application is now ready for production deployment."




