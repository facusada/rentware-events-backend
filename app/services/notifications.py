class NotificationService:
    def __init__(self):
        pass

    async def send_reservation_confirmation(self, order_code: str, channel: str = "email") -> None:
        # Stub: wire up email/whatsapp provider here
        return None

    async def send_delivery_notice(self, order_code: str, channel: str = "email") -> None:
        return None
