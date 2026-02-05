from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib import messages
from django.utils.html import format_html
from .models import User, Service, Action, Validation, Notification



def validate_users(modeladmin, request, queryset):
    """
    Action admin pour valider les utilisateurs sélectionnés.
    """
    updated = queryset.update(is_validated=True)
    messages.success(request, f'{updated} utilisateur(s) validé(s) avec succès.')

validate_users.short_description = "✓ Valider les utilisateurs sélectionnés"


def assign_role_user(modeladmin, request, queryset):
    """
    Attribuer le rôle 'Utilisateur' aux utilisateurs sélectionnés.
    """
    updated = queryset.update(role='user')
    messages.success(request, f'{updated} utilisateur(s) ont reçu le rôle "Utilisateur".')

assign_role_user.short_description = "👤 Attribuer le rôle: Utilisateur"


def assign_role_validator(modeladmin, request, queryset):
    """
    Attribuer le rôle 'Validateur' aux utilisateurs sélectionnés.
    """
    updated = queryset.update(role='validator')
    messages.success(request, f'{updated} utilisateur(s) ont reçu le rôle "Validateur".')

assign_role_validator.short_description = "✓ Attribuer le rôle: Validateur"


def assign_role_admin(modeladmin, request, queryset):
    """
    Attribuer le rôle 'Administrateur' aux utilisateurs sélectionnés.
    """
    updated = queryset.update(role='admin')
    messages.success(request, f'{updated} utilisateur(s) ont reçu le rôle "Administrateur".')

assign_role_admin.short_description = "⚙️ Attribuer le rôle: Administrateur"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin configuration.
    """
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_validated', 'is_staff', 'is_active']
    list_filter = ['role', 'is_validated', 'is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    actions = [validate_users, assign_role_user, assign_role_validator, assign_role_admin]
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('role', 'is_validated'),
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('role', 'is_validated'),
        }),
    )
    
    def get_queryset(self, request):
        """
        Highlight pending validations in the admin.
        """
        qs = super().get_queryset(request)
        return qs


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """
    Service admin configuration.
    """
    list_display = ['user', 'date_ouverture', 'date_fermeture', 'statut', 'get_remaining_display']
    list_filter = ['statut', 'date_ouverture']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['date_ouverture']
    date_hierarchy = 'date_ouverture'
    
    def get_remaining_display(self, obj):
        """
        Display remaining time in admin list.
        """
        return obj.get_remaining_time_display()
    get_remaining_display.short_description = 'Temps restant'
    
    def get_readonly_fields(self, request, obj=None):
        """
        Make closed services read-only.
        """
        if obj and obj.statut == 'fermé':
            return ['user', 'date_ouverture', 'date_fermeture', 'statut']
        return ['date_ouverture']
    
    def has_delete_permission(self, request, obj=None):
        """
        Prevent deletion of closed services.
        """
        if obj and obj.statut == 'fermé':
            return False
        return super().has_delete_permission(request, obj)


# Validation inline for Action admin
class ValidationInline(admin.TabularInline):
    model = Validation
    extra = 0
    readonly_fields = ['validateur', 'statut', 'commentaire', 'date_validation']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# Admin actions for validation
def validate_actions(modeladmin, request, queryset):
    """
    Valider les actions sélectionnées.
    """
    from .models import Validation
    
    count = 0
    warnings = []
    
    for action in queryset:
        # Check if already validated
        if action.validation_status == 'validé':
            continue
        
        # Check for self-validation
        if action.auteur == request.user:
            warnings.append(f"⚠️ Auto-validation détectée pour l'action #{action.id}")
        
        # Create validation
        Validation.objects.create(
            action=action,
            validateur=request.user,
            statut='validé'
        )
        count += 1
    
    messages.success(request, f'{count} action(s) validée(s) avec succès.')
    if warnings:
        for warning in warnings:
            messages.warning(request, warning)

validate_actions.short_description = "✓ Valider les actions sélectionnées"


def reject_actions(modeladmin, request, queryset):
    """
    Refuser les actions sélectionnées (nécessite un commentaire).
    """
    # This will be handled via a custom view for comment input
    messages.warning(
        request,
        'Pour refuser une action, veuillez la sélectionner individuellement '
        'et utiliser le formulaire de refus avec commentaire.'
    )

reject_actions.short_description = "✗ Refuser les actions sélectionnées"


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    """
    Action admin configuration.
    """
    list_display = ['id', 'auteur', 'categorie', 'statut', 'get_description_preview', 'suivi', 'date_creation', 'get_validation_badge']
    list_filter = ['categorie', 'statut', 'suivi', 'date_creation', 'auteur', 'service__statut']
    search_fields = ['auteur__username', 'description', 'cause', 'personnes_impliquees']
    readonly_fields = ['date_creation', 'date_modification']
    inlines = [ValidationInline]
    actions = [validate_actions, reject_actions]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('auteur', 'service', 'categorie', 'statut')
        }),
        ('Détails de l\'action', {
            'fields': ('description', 'cause', 'personnes_impliquees', 'suivi')
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    def get_description_preview(self, obj):
        """
        Show preview of description.
        """
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description
    get_description_preview.short_description = 'Description'
    
    def get_validation_badge(self, obj):
        """
        Display validation status as colored badge.
        """
        status = obj.validation_status
        colors = {
            'en_attente': '#f59e0b',  # Orange
            'validé': '#10b981',      # Green
            'refusé': '#ef4444',      # Red
        }
        labels = {
            'en_attente': 'En attente',
            'validé': 'Validé',
            'refusé': 'Refusé',
        }
        color = colors.get(status, '#64748b')
        label = labels.get(status, status)
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px; font-weight: 500;">{}</span>',
            color, label
        )
    get_validation_badge.short_description = 'Validation'
    
    def get_readonly_fields(self, request, obj=None):
        """
        Make validated actions read-only.
        """
        if obj and obj.validation_status == 'validé':
            return ['auteur', 'service', 'categorie', 'description', 'cause', 
                    'personnes_impliquees', 'statut', 'suivi', 'date_creation', 'date_modification']
        return ['date_creation', 'date_modification']



@admin.register(Validation)
class ValidationAdmin(admin.ModelAdmin):
    """
    Validation admin configuration.
    """
    list_display = ['id', 'action', 'validateur', 'statut', 'date_validation', 'get_self_validation_badge']
    list_filter = ['statut', 'date_validation', 'validateur']
    search_fields = ['action__description', 'validateur__username', 'commentaire']
    readonly_fields = ['action', 'validateur', 'statut', 'commentaire', 'date_validation']
    
    def get_self_validation_badge(self, obj):
        """
        Display warning if self-validation.
        """
        if obj.is_self_validation():
            return format_html(
                '<span style="background-color: #f59e0b; color: white; padding: 3px 8px; '
                'border-radius: 12px; font-size: 11px; font-weight: 500;">⚠️ Auto-validation</span>'
            )
        return '-'
    get_self_validation_badge.short_description = 'Avertissement'
    
    def has_add_permission(self, request):
        """
        Prevent manual creation of validations.
        """
        return False
    
    def has_delete_permission(self, request, obj=None):
        """
        Prevent deletion of validations (immutable audit trail).
        """
        return False
    
    def has_change_permission(self, request, obj=None):
        """
        Prevent modification of validations (immutable audit trail).
        """
        return False


# Admin actions for notifications
def mark_as_read(modeladmin, request, queryset):
    """
    Marquer les notifications sélectionnées comme lues.
    """
    updated = queryset.update(lue=True)
    messages.success(request, f'{updated} notification(s) marquée(s) comme lue(s).')

mark_as_read.short_description = "✓ Marquer comme lue(s)"


def mark_as_unread(modeladmin, request, queryset):
    """
    Marquer les notifications sélectionnées comme non lues.
    """
    updated = queryset.update(lue=False)
    messages.success(request, f'{updated} notification(s) marquée(s) comme non lue(s).')

mark_as_unread.short_description = "● Marquer comme non lue(s)"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Notification admin configuration.
    """
    list_display = ['id', 'get_status_icon', 'destinataire', 'type', 'get_message_preview', 'date']
    list_filter = ['type', 'lue', 'date', 'destinataire']
    search_fields = ['destinataire__username', 'message']
    readonly_fields = ['destinataire', 'type', 'message', 'date', 'action', 'validation']
    actions = [mark_as_read, mark_as_unread]
    date_hierarchy = 'date'
    
    def get_status_icon(self, obj):
        """
        Display read/unread status icon.
        """
        if obj.lue:
            return format_html(
                '<span style="color: #10b981; font-size: 16px;" title="Lue">✓</span>'
            )
        else:
            return format_html(
                '<span style="color: #f59e0b; font-size: 16px;" title="Non lue">●</span>'
            )
    get_status_icon.short_description = 'Statut'
    
    def get_message_preview(self, obj):
        """
        Show preview of message.
        """
        if len(obj.message) > 80:
            return obj.message[:80] + '...'
        return obj.message
    get_message_preview.short_description = 'Message'
    
    def has_add_permission(self, request):
        """
        Prevent manual creation of notifications (created via signals).
        """
        return False

