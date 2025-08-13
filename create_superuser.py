#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Delete existing user if exists
User.objects.filter(email='admin@admin.com').delete()

# Create new superuser
user = User.objects.create_superuser(
    email='admin@admin.com',
    password='admin'
)

print(f'Superuser created successfully: {user.email}')
print('Email: admin@admin.com')
print('Password: admin')

