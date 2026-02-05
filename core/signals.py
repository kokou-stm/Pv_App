from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Validation, Action, Notification, User
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def send_websocket_notification(user, notification_data, unread_count):
    """
    Send a notification to a user via WebSocket.
    
    Args:
        user: User to notify
        notification_data: Dictionary containing notification details
        unread_count: Current unread notification count
    """
    channel_layer = get_channel_layer()
    group_name = f'notifications_{user.id}'
    
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'notification_message',
            'notification': notification_data,
            'count': unread_count
        }
    )


@receiver(post_save, sender=Validation)
def create_validation_notification(sender, instance, created, **kwargs):
    """
    Create notification when a validation is created or updated.
    Notifies the action author about validation, rejection, or comment.
    """
    if created:
        action = instance.action
        author = action.auteur
        
        # Don't notify if the validator is the author (self-validation)
        if instance.validateur == author:
            return
        
        # Determine notification type and message
        if instance.statut == 'validé':
            notif_type = 'validation'
            message = f"Votre action du {action.date_creation.strftime('%d/%m/%Y à %H:%M')} a été validée par {instance.validateur.username}."
        elif instance.statut == 'refusé':
            notif_type = 'refus'
            message = f"Votre action du {action.date_creation.strftime('%d/%m/%Y à %H:%M')} a été refusée par {instance.validateur.username}."
            if instance.commentaire:
                message += f"\n\nCommentaire : {instance.commentaire}"
        else:  # en_attente with comment
            notif_type = 'commentaire'
            message = f"{instance.validateur.username} a commenté votre action du {action.date_creation.strftime('%d/%m/%Y à %H:%M')}."
            if instance.commentaire:
                message += f"\n\nCommentaire : {instance.commentaire}"
        
        # Create notification in database
        notification = Notification.objects.create(
            destinataire=author,
            type=notif_type,
            message=message,
            action=action,
            validation=instance
        )
        
        # Send via WebSocket
        unread_count = Notification.objects.filter(destinataire=author, lue=False).count()
        send_websocket_notification(
            author,
            {
                'id': notification.id,
                'type': notif_type,
                'message': message,
                'date': notification.date.isoformat(),
                'icon': notification.get_icon(),
            },
            unread_count
        )


@receiver(post_save, sender=Action)
def create_new_action_notification(sender, instance, created, **kwargs):
    """
    Create notification for admins when a new action is created.
    """
    if created:
        # Get all admin users
        admins = User.objects.filter(role='admin', is_validated=True)
        
        # Don't notify the author
        admins = admins.exclude(id=instance.auteur.id)
        
        # Create notification for each admin
        for admin in admins:
            message = f"Nouvelle action créée par {instance.auteur.username} le {instance.date_creation.strftime('%d/%m/%Y à %H:%M')}."
            if len(instance.description) > 100:
                message += f"\nDescription : {instance.description[:100]}..."
            else:
                message += f"\nDescription : {instance.description}"
            
            # Create notification in database
            notification = Notification.objects.create(
                destinataire=admin,
                type='nouvelle_action',
                message=message,
                action=instance
            )
            
            # Send via WebSocket
            unread_count = Notification.objects.filter(destinataire=admin, lue=False).count()
            send_websocket_notification(
                admin,
                {
                    'id': notification.id,
                    'type': 'nouvelle_action',
                    'message': message,
                    'date': notification.date.isoformat(),
                    'icon': notification.get_icon(),
                },
                unread_count
            )


def notify_user(user, notif_type, message, action=None, validation=None):
    """
    Helper function to create a notification.
    
    Args:
        user: User to notify
        notif_type: Type of notification ('validation', 'refus', 'commentaire', 'nouvelle_action')
        message: Notification message
        action: Related action (optional)
        validation: Related validation (optional)
    """
    notification = Notification.objects.create(
        destinataire=user,
        type=notif_type,
        message=message,
        action=action,
        validation=validation
    )
    
    # Send via WebSocket
    unread_count = Notification.objects.filter(destinataire=user, lue=False).count()
    send_websocket_notification(
        user,
        {
            'id': notification.id,
            'type': notif_type,
            'message': message,
            'date': notification.date.isoformat(),
            'icon': notification.get_icon(),
        },
        unread_count
    )
