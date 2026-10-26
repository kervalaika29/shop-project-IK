from django.apps import AppConfig


class ShopConfig(AppConfig):
    name = "shop"

    def ready(self):
        # signal-ების დარეგისტრირება (სურათის ფაილების გასუფთავება)
        from . import signals  # noqa: F401
