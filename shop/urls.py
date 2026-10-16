from django.urls import path

from . import views

urlpatterns = [
    # გვერდები (HW36)
    path("", views.home, name="home"),
    path("category/<int:pk>/", views.category_detail, name="category_detail"),
    path("sale/", views.sale, name="sale"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    # პროდუქტის დამატება / განახლება / წაშლა (HW37)
    path("product/add/", views.product_create, name="product_create"),
    path("product/<int:pk>/edit/", views.product_update, name="product_update"),
    path("product/<int:pk>/delete/", views.product_delete, name="product_delete"),
    # შაბლონის დანარჩენი გვერდები (ლოგიკის გარეშე)
    path("cart/", views.cart, name="cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("contact/", views.contact, name="contact"),
]
