from django.shortcuts import redirect
from django.urls import reverse


class ValidatedUserMiddleware:
    """
    Middleware pour bloquer l'accès aux pages protégées pour les utilisateurs non validés.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs publiques accessibles sans validation
        self.public_urls = [
            reverse('login'),
            reverse('register'),
            reverse('logout'),
            '/admin/',
            '/static/',
        ]
    
    def __call__(self, request):
        # Vérifier si l'utilisateur est authentifié
        if request.user.is_authenticated:
            # Vérifier si l'URL actuelle est publique
            is_public = any(request.path.startswith(url) for url in self.public_urls)
            
            # Si l'utilisateur n'est pas validé et essaie d'accéder à une page protégée
            if not request.user.is_validated and not is_public and not request.user.is_staff:
                # Rediriger vers la page d'attente de validation
                return redirect('login')
        
        response = self.get_response(request)
        return response
