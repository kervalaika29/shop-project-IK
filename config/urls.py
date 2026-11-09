from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("users.urls")),
    # REST API (HW45): /api/categories/, /api/products/, ...
    path("api/", include("api.urls")),
    # DRF-ის ჩაშენებული შესვლა/გასვლა ბრაუზერული API-ისთვის (/api-auth/login/): ნამდვილი
    # მომხმარებლით შესვლის შემდეგ ბრაუზერიდან პროდუქტის შექმნა (POST) შეიძლება
    path("api-auth/", include("rest_framework.urls")),
    path("", include("shop.urls")),
]

# დეველოპმენტის დროს (DEBUG=True) ატვირთულ სურათებს (/media/...) Django თვითონ აწვდის.
# DEBUG=False-ზე ეს ფუნქცია ცარიელ სიას აბრუნებს, პროდაქშენში მედიას ვებსერვერი უნდა აწვდიდეს.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
