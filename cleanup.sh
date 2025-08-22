#!/bin/bash

# Cleanup script for ClearInsight

echo "🧹 Starting cleanup..."

# Remove Python cache files
echo "🗑️  Removing Python cache files..."
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove temporary files
echo "🗑️  Removing temporary files..."
rm -rf temp_uploads/*
rm -rf staticfiles/*

# Remove development files
echo "🗑️  Removing development files..."
rm -f .eslintrc.cjs .prettierrc.cjs .prettierignore 2>/dev/null || true

# Remove test files
echo "🗑️  Removing test files..."
rm -f test_*.py demo_*.py test_*.html 2>/dev/null || true

# Remove documentation files (keep README.md)
echo "🗑️  Removing documentation files..."
rm -f VIDEO_PLAYER_TEST_SUMMARY.md IMPLEMENTATION_SUMMARY.md nexttask.md plan.md 2>/dev/null || true

# Remove sample pages
echo "🗑️  Removing sample pages..."
rm -rf samplepages/ 2>/dev/null || true

# Clean Docker
echo "🐳 Cleaning Docker..."
docker system prune -f 2>/dev/null || true

# Remove old database (will be recreated with PostgreSQL)
echo "🗄️  Removing old SQLite database..."
rm -f db.sqlite3 2>/dev/null || true

echo "✅ Cleanup completed!"
echo "📝 Note: This script removes development and test files."
echo "   For production deployment, use the Docker setup."

