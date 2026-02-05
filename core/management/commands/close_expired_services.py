from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Service


class Command(BaseCommand):
    help = 'Ferme automatiquement les services expirés (date_fermeture dépassée)'

    def handle(self, *args, **options):
        """
        Find and close all expired services.
        """
        # Find all open services that have expired
        expired_services = Service.objects.filter(
            statut='ouvert',
            date_fermeture__lt=timezone.now()
        )
        
        count = expired_services.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('Aucun service expiré trouvé.')
            )
            return
        
        # Close all expired services
        for service in expired_services:
            service.close_service()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Service fermé: {service.user.username} '
                    f'(ouvert le {service.date_ouverture.strftime("%d/%m/%Y %H:%M")})'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ {count} service(s) expiré(s) fermé(s) avec succès.'
            )
        )
