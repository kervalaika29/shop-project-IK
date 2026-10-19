from django.urls import path

from . import views

urlpatterns = [
    # გვერდები (HW36) — HW39-ში Class-Based View-ებად გადაკეთდა
    path("", views.HomeView.as_view(), name="home"),
    path("category/<int:pk>/", views.CategoryDetailView.as_view(), name="category_detail"),
    path("sale/", views.SaleView.as_view(), name="sale"),
    path("product/<int:pk>/", views.ProductDetailView.as_view(), name="product_detail"),
    # პროდუქტის დამატება (CBV) / განახლება / წაშლა (HW37; update და delete function-based რჩება)
    path("product/add/", views.ProductCreateView.as_view(), name="product_create"),
    path("product/<int:pk>/edit/", views.product_update, name="product_update"),
    path("product/<int:pk>/delete/", views.product_delete, name="product_delete"),
    # შაბლონის დანარჩენი გვერდები (ლოგიკის გარეშე)
    path("cart/", views.CartView.as_view(), name="cart"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("contact/", views.ContactView.as_view(), name="contact"),
]
