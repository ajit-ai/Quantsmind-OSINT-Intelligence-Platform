from channels.generic.websocket import AsyncJsonWebsocketConsumer
class AlertConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close(); return
        await self.channel_layer.group_add(f"user_{self.scope['user'].id}", self.channel_name)
        await self.accept()
    async def disconnect(self, code):
        if self.scope["user"].is_authenticated:
            await self.channel_layer.group_discard(f"user_{self.scope['user'].id}", self.channel_name)
    async def alert_message(self, event):
        await self.send_json(event["data"])
