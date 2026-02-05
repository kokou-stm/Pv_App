#!/bin/bash

# Attendre que la base de données soit prête (si nécessaire)
echo "Waiting for database..."
sleep 2

# Exécuter les migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Créer un superuser si nécessaire (optionnel)
echo "Creating superuser if needed..."
python manage.py shell << END
from core.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
    print('Superuser created')
else:
    print('Superuser already exists')
END

# Collecter les fichiers statiques
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Démarrer le serveur
echo "Starting server..."
exec python manage.py runserver 0.0.0.0:80
