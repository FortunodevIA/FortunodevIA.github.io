#!/usr/bin/env python
"""Utilitaire en ligne de commande Django pour les tâches administratives."""
import os
import sys


def main():
    """Exécute les tâches administratives."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eduquiz.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Impossible d'importer Django. Vérifie qu'il est installé et "
            "qu'il est disponible sur ta variable PYTHONPATH. As-tu "
            "activé l'environnement virtuel ?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
