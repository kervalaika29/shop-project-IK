from django.urls import path

from . import views

# app_name: მისამართების სახელები "api:" პრეფიქსით გამოიყენება (მაგ. reverse("api:product-list")),
# ამიტომ საიტის სახელებს (home, product_detail, ...) არ ეჯახება.
app_name = "api"

urlpatterns = [
    path("", views.api_root, name="root"),
    # კატეგორიების სია
    path("categories/", views.CategoryListAPIView.as_view(), name="category-list"),
    # პროდუქტები: სია, შექმნა და დეტალები. "products/create/" "products/<int:pk>/"-ს არ ეჯახება:
    # <int:pk> მხოლოდ რიცხვს იღებს.
    path("products/", views.ProductListAPIView.as_view(), name="product-list"),
    path("products/create/", views.ProductCreateAPIView.as_view(), name="product-create"),
    path("products/<int:pk>/", views.ProductDetailAPIView.as_view(), name="product-detail"),
]
