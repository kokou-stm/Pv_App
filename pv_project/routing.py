"""
WebSocket URL routing for the PV project.
"""

from django.urls import path
from core import consumers

websocket_urlpatterns = [
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
]
