# PV en Ligne - Projet Django

Système de gestion de procès-verbaux en ligne avec authentification personnalisée.

## Installation

1. Créer et activer l'environnement virtuel :
```bash
python3 -m venv venv
source venv/bin/activate  # Sur macOS/Linux
```

2. Installer les dépendances :
```bash
pip install django
```

3. Appliquer les migrations :
```bash
python manage.py migrate
```

4. Créer un superuser :
```bash
python manage.py createsuperuser
```

5. Lancer le serveur de développement :
```bash
python manage.py runserver
```

## Fonctionnalités

### Phase 0 - Fondation Technique ✅

- ✅ Modèle User personnalisé avec champs `role` et `is_validated`
- ✅ Interface d'administration Django configurée
- ✅ Système d'authentification fonctionnel

### Rôles Utilisateurs

- **admin** : Administrateur
- **user** : Utilisateur (par défaut)
- **validator** : Validateur

### Validation des Utilisateurs

Le champ `is_validated` permet de contrôler l'accès au site. Les utilisateurs non validés pourront être bloqués via un middleware (à implémenter dans une phase future).

## Structure du Projet

```
pv/
├── venv/                    # Environnement virtuel
├── manage.py                # Script de gestion Django
├── pv_project/              # Configuration du projet
│   └── settings.py          # Paramètres (AUTH_USER_MODEL configuré)
├── core/                    # Application principale
│   ├── models.py            # Modèle User personnalisé
│   └── admin.py             # Configuration admin
└── db.sqlite3               # Base de données SQLite
```

## Accès Admin

URL : http://127.0.0.1:8000/admin/

L'interface admin permet de :
- Gérer les utilisateurs
- Attribuer des rôles
- Valider/invalider des utilisateurs
- Filtrer par rôle, statut de validation, etc.

## Développement

### Commandes Utiles

```bash
# Créer des migrations
python manage.py makemigrations

# Appliquer les migrations
python manage.py migrate

# Lancer le serveur
python manage.py runserver

# Accéder au shell Django
python manage.py shell
```

## Prochaines Phases

- [ ] Middleware de validation des utilisateurs
- [ ] Vues et templates frontend
- [ ] Gestion des permissions par rôle
- [ ] Modèles de données pour les PV
