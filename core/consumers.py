"""
WebSocket consumers for real-time notifications.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    Each user gets their own notification group.
    """
    
    async def connect(self):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        self.user = self.scope['user']
        
        # Only allow authenticated users
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Create a unique group name for this user
        self.group_name = f'notifications_{self.user.id}'
        
        # Join the user's notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        """
        Called when the WebSocket closes for any reason.
        """
        if hasattr(self, 'group_name'):
            # Leave the notification group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        Called when we receive a message from the WebSocket.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'get_unread_count':
                # Client is requesting the current unread count
                unread_count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': unread_count
                }))
        except json.JSONDecodeError:
            pass
    
    async def notification_message(self, event):
        """
        Called when a notification is sent to the group.
        This is triggered by channel_layer.group_send()
        """
        # Send the notification to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification'],
            'count': event['count']
        }))
    
    @database_sync_to_async
    def get_unread_count(self):
        """
        Get the number of unread notifications for the current user.
        """
        return Notification.objects.filter(
            destinataire=self.user,
            lue=False
        ).count()
