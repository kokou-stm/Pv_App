from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError


class User(AbstractUser):
    """
    Custom User model with role-based access and validation status.
    """
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('user', 'Utilisateur'),
        ('validator', 'Validateur'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        verbose_name='Rôle'
    )
    is_validated = models.BooleanField(
        default=False,
        verbose_name='Validé'
    )
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Service(models.Model):
    """
    Service model for 24-hour service periods.
    Each user can only have one active service at a time.
    """
    STATUT_CHOICES = [
        ('ouvert', 'Ouvert'),
        ('fermé', 'Fermé'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name='Utilisateur'
    )
    date_ouverture = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date d\'ouverture'
    )
    date_fermeture = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Date de fermeture'
    )
    statut = models.CharField(
        max_length=10,
        choices=STATUT_CHOICES,
        default='ouvert',
        verbose_name='Statut'
    )
    
    class Meta:
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        ordering = ['-date_ouverture']
    
    def __str__(self):
        return f"Service de {self.user.username} - {self.get_statut_display()} ({self.date_ouverture.strftime('%d/%m/%Y %H:%M')})"
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically set date_fermeture to 24h after opening.
        """
        if not self.pk:  # Only on creation
            if not self.date_fermeture:
                self.date_fermeture = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def clean(self):
        """
        Validate that user doesn't have another active service.
        """
        if self.statut == 'ouvert':
            # Check for other active services for this user
            active_services = Service.objects.filter(
                user=self.user,
                statut='ouvert'
            ).exclude(pk=self.pk)
            
            if active_services.exists():
                raise ValidationError(
                    'Cet utilisateur a déjà un service actif. '
                    'Veuillez fermer le service actuel avant d\'en ouvrir un nouveau.'
                )
    
    def is_active(self):
        """
        Check if the service is currently active (open and not expired).
        """
        return self.statut == 'ouvert' and self.date_fermeture > timezone.now()
    
    def is_expired(self):
        """
        Check if the service has expired (past date_fermeture).
        """
        return timezone.now() > self.date_fermeture
    
    def close_service(self):
        """
        Close the service.
        """
        self.statut = 'fermé'
        self.save()
    
    def get_remaining_time(self):
        """
        Get the remaining time until service closure.
        Returns a timedelta object or None if service is closed.
        """
        if self.statut == 'fermé':
            return None
        
        remaining = self.date_fermeture - timezone.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def get_remaining_time_display(self):
        """
        Get a human-readable display of remaining time.
        """
        remaining = self.get_remaining_time()
        if remaining is None:
            return "Service fermé"
        
        if remaining.total_seconds() <= 0:
            return "Expiré"
        
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}min restantes"
        else:
            return f"{minutes}min restantes"


class Action(models.Model):
    """
    Action model for PV entries.
    Represents individual actions/entries created during a service period.
    """
    CATEGORIE_CHOICES = [
        ('panne', 'Panne'),
        ('maintenance', 'Maintenance'),
        ('incident', 'Incident'),
        ('suivi', 'Suivi'),
        ('autre', 'Autre'),
    ]
    
    STATUT_CHOICES = [
        ('resolu', 'Résolu'),
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
    ]
    
    auteur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='actions',
        verbose_name='Auteur'
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='actions',
        verbose_name='Service'
    )
    categorie = models.CharField(
        max_length=20,
        choices=CATEGORIE_CHOICES,
        default='autre',
        verbose_name='Catégorie'
    )
    description = models.TextField(
        verbose_name='Description'
    )
    cause = models.TextField(
        blank=True,
        null=True,
        verbose_name='Cause supposée ou identifiée'
    )
    personnes_impliquees = models.TextField(
        blank=True,
        null=True,
        verbose_name='Personnes impliquées'
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name='Statut'
    )
    suivi = models.BooleanField(
        default=False,
        verbose_name='Nécessite un suivi'
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de création'
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name='Date de modification'
    )
    
    class Meta:
        verbose_name = 'Action'
        verbose_name_plural = 'Actions'
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Action de {self.auteur.username} - {self.date_creation.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def validation_status(self):
        """
        Get current validation status.
        Returns: 'en_attente', 'validé', or 'refusé'
        """
        latest = self.latest_validation
        if latest:
            return latest.statut
        return 'en_attente'
    
    @property
    def latest_validation(self):
        """
        Get the most recent validation for this action.
        """
        return self.validations.order_by('-date_validation').first()
    
    def get_validation_history(self):
        """
        Get all validations for this action in chronological order.
        """
        return self.validations.order_by('date_validation')
    
    def can_be_edited(self):
        """
        Check if action can still be edited.
        Actions can be edited if not validated or if rejected.
        """
        status = self.validation_status
        return status in ['en_attente', 'refusé']


class Validation(models.Model):
    """
    Validation model for action approval workflow.
    Tracks all validation actions (approve, reject, comment) by admins.
    """
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('validé', 'Validé'),
        ('refusé', 'Refusé'),
    ]
    
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name='validations',
        verbose_name='Action'
    )
    validateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='validations_effectuees',
        verbose_name='Validateur'
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name='Statut'
    )
    commentaire = models.TextField(
        blank=True,
        null=True,
        verbose_name='Commentaire'
    )
    date_validation = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de validation'
    )
    
    class Meta:
        verbose_name = 'Validation'
        verbose_name_plural = 'Validations'
        ordering = ['-date_validation']
    
    def __str__(self):
        return f"{self.get_statut_display()} par {self.validateur.username} - {self.date_validation.strftime('%d/%m/%Y %H:%M')}"
    
    def is_self_validation(self):
        """
        Check if the validator is the same as the action author.
        Returns True if self-validation.
        """
        return self.validateur == self.action.auteur
    
    def clean(self):
        """
        Validate before saving.
        """
        # Require comment for rejections
        if self.statut == 'refusé' and not self.commentaire:
            raise ValidationError(
                'Un commentaire est obligatoire pour refuser une action.'
            )
        
        # Check if validator is admin
        if self.validateur.role != 'admin':
            raise ValidationError(
                'Seuls les administrateurs peuvent valider des actions.'
            )
    
    @staticmethod
    def can_validate(user):
        """
        Check if user has permission to validate.
        """
        return user.role == 'admin'


class Notification(models.Model):
    """
    Notification model to inform users of important events.
    """
    TYPE_CHOICES = [
        ('validation', 'Validation d\'action'),
        ('refus', 'Refus d\'action'),
        ('commentaire', 'Nouveau commentaire'),
        ('nouvelle_action', 'Nouvelle action'),
    ]
    
    destinataire = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Destinataire'
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name='Type'
    )
    message = models.TextField(
        verbose_name='Message'
    )
    lue = models.BooleanField(
        default=False,
        verbose_name='Lue'
    )
    date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date'
    )
    
    # Optional links to related objects
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='Action'
    )
    validation = models.ForeignKey(
        Validation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='Validation'
    )
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
    
    def __str__(self):
        status = "✓" if self.lue else "●"
        return f"{status} {self.get_type_display()} pour {self.destinataire.username} - {self.date.strftime('%d/%m/%Y %H:%M')}"
    
    def get_icon(self):
        """
        Get the icon class for this notification type.
        """
        icons = {
            'validation': '✓',
            'refus': '✗',
            'commentaire': '💬',
            'nouvelle_action': '📝',
        }
        return icons.get(self.type, '📌')
    
    def get_url(self):
        """
        Get the URL to view the related object.
        """
        if self.action:
            return f'/consultation/actions/?action={self.action.id}'
        elif self.validation:
            return f'/validations/history/{self.validation.action.id}/'
        return '/notifications/'

