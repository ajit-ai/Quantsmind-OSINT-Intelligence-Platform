import json
import urllib.parse
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

# JWT auth for WS: supports ?token=<JWT> or Authorization: Bearer <JWT> header
# plus fallback to session auth (AuthMiddlewareStack)

class AlertConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        # try JWT from query string if user not authenticated via session
        if not user or not user.is_authenticated:
            token = None
            qs = self.scope.get("query_string", b"").decode()
            if qs:
                try:
                    params = urllib.parse.parse_qs(qs)
                    token = (params.get("token") or [None])[0]
                except Exception:
                    pass
            if not token:
                # header fallback
                headers = dict((k.decode(), v.decode()) for k,v in self.scope.get("headers", []))
                auth = headers.get("authorization", "") or headers.get("Authorization", "")
                if auth.startswith("Bearer "):
                    token = auth.split(" ",1)[1]
            if token:
                user = await self._get_user_from_token(token)
                if user:
                    self.scope["user"] = user
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # heartbeat: send connected ack
        await self.send_json({"type":"connected","user": str(user.id), "group": self.group_name})

    @database_sync_to_async
    def _get_user_from_token(self, token):
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth import get_user_model
            at = AccessToken(token)
            uid = at.get("user_id")
            User = get_user_model()
            return User.objects.filter(id=uid, is_active=True).first()
        except Exception:
            return None

    async def disconnect(self, code):
        user = self.scope.get("user")
        if user and getattr(user, "is_authenticated", False):
            try:
                await self.channel_layer.group_discard(f"user_{user.id}", self.channel_name)
            except Exception:
                pass

    async def receive_json(self, content, **kwargs):
        # client pings / watchlist subscribe acks
        action = content.get("action")
        if action == "ping":
            await self.send_json({"type":"pong"})
        elif action == "subscribe":
            await self.send_json({"type":"subscribed","group": getattr(self, "group_name", "")})

    async def alert_message(self, event):
        # event: {"type":"alert.message","data":{...}}
        try:
            await self.send_json(event.get("data") or event)
        except Exception:
            pass

    async def notification(self, event):
        await self.send_json(event.get("data") or event)
