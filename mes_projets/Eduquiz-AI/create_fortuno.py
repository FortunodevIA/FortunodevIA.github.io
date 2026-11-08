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
    if not User.objects.filter(username='fortuno').exists():
        User.objects.create_superuser('fortuno', 'fortuno@example.com', 'president1850')
        print('✅ Superuser créé avec succès!')
        print('Username: fortuno')
        print('Password: president1850')
    else:
        user = User.objects.get(username='fortuno')
        user.set_password('president1850')
        user.save()
        print('✅ Superuser fortuno modifié!')
        print('Password: president1850')
except Exception as e:
    print(f'❌ Erreur: {e}')
