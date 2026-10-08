from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("category/<int:pk>/", views.category_detail, name="category_detail"),
    path("sale/", views.sale, name="sale"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
]
