from django.apps import AppConfig


class ShopConfig(AppConfig):
    name = "shop"

    def ready(self):
        # signal-ების დარეგისტრირება (პროდუქტის განახლების შეტყობინება, სურათის ფაილების გასუფთავება)
        from . import signals  # noqa: F401
