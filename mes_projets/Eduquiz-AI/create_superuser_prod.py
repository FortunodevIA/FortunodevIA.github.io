#!/usr/bin/env python
import os
import django

# Ne définissez pas DATABASE_URL en dur dans le code.
# Utilisez une variable d'environnement sécurisée à la place.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eduquiz.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print('✅ Superuser créé avec succès!')
        print('Username: admin')
        print('Password: admin123')
    else:
        print('⚠️ Superuser admin existe déjà')
        # Option pour changer le password
        user = User.objects.get(username='admin')
        user.set_password('admin123')
        user.save()
        print('✅ Mot de passe réinitialisé: admin123')
except Exception as e:
    print(f'❌ Erreur: {e}')
