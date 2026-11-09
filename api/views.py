"""
API view-ები (HW45), Django REST Framework-ის generic კლასებზე.

generic view თავისი საქმის უმეტესს თვითონ აკეთებს: queryset-ს იღებს, მას serializer_class-ით JSON-ად
აქცევს, 404-ს და შეცდომებს აბრუნებს. ჩვენ მხოლოდ ვწერთ, რომელი მონაცემი და რომელი სერიალიზატორი:

    CategoryListAPIView   GET   /api/categories/        კატეგორიების სია
    ProductListAPIView    GET   /api/products/          პროდუქტების სია
    ProductDetailAPIView  GET   /api/products/<id>/     ერთი პროდუქტის დეტალური ინფორმაცია
    ProductCreateAPIView  POST  /api/products/create/   პროდუქტის შექმნა (მხოლოდ ავტორიზებულს)

წაკითხვა ყველას შეუძლია, შექმნა კი მხოლოდ ავტორიზებულს: საიტზეც ასეა (HW41). ეს წესი
settings.py-ში REST_FRAMEWORK-ის სტანდარტული IsAuthenticatedOrReadOnly-ითაა, შექმნის view-ზე
კი კიდევ უფრო მკაცრია (IsAuthenticated).
"""

from django.db.models import Count
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse

from shop.models import Category, Product

from .serializers import (
    CategoryListSerializer,
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


@api_view(["GET"])
def api_root(request):
    """/api/ : ყველა endpoint-ის ბმული ერთ ადგილას (ბრაუზერში მათზე დაწკაპუნებით გადადიხართ)."""
    return Response(
        {
            "categories": reverse("api:category-list", request=request),
            "products": reverse("api:product-list", request=request),
            "product_create": reverse("api:product-create", request=request),
        }
    )


class CategoryListAPIView(generics.ListAPIView):
    """
    კატეგორიების სია. ყველა კატეგორია ბრუნდება, ცარიელებიც (საიტის მენიუში ცარიელი კატეგორიები
    არ ჩანს, API-ში კი სჭირდება: პროდუქტის შესაქმნელად კატეგორიის id აუცილებელია). product_count
    თითოეულ კატეგორიას ბაზიდან ერთი მოთხოვნით მოჰყვება.
    """

    # order_by აუცილებელია: annotate-ის (GROUP BY) შემდეგ Meta.ordering აღარ მოქმედებს
    queryset = Category.objects.annotate(product_count=Count("products")).order_by("name")
    serializer_class = CategoryListSerializer


class ProductListAPIView(generics.ListAPIView):
    """
    პროდუქტების სია, ფასის ზრდადობით (ისევე, როგორც საიტის მთავარ გვერდზე). select_related
    კატეგორიას პროდუქტებთან ერთად იღებს, ამიტომ ბაზაში ერთი მოთხოვნა სრულდება და არა 1 + N.
    """

    queryset = Product.objects.select_related("category").order_by("price", "pk")
    serializer_class = ProductListSerializer


class ProductDetailAPIView(generics.RetrieveAPIView):
    """ერთი პროდუქტის დეტალური ინფორმაცია id-ით. არარსებულ id-ზე 404."""

    queryset = Product.objects.select_related("category", "user")
    serializer_class = ProductDetailSerializer


class ProductCreateAPIView(generics.CreateAPIView):
    """
    პროდუქტის შექმნა. მხოლოდ ავტორიზებული მომხმარებლისთვის: ანონიმური 403-ს იღებს და
    არაფერი ინახება. მფლობელი (user) ავტომატურად ის მომხმარებელია, ვინც მოთხოვნა გამოაგზავნა.

    მონაცემებს ამოწმებს ProductCreateSerializer. წარმატებისას პასუხი 201 Created-ია და
    მასში პროდუქტის სრული ინფორმაციაა (ProductDetailSerializer), ისევე როგორც დეტალურ API-ში.
    სურათის ასატვირთად მოთხოვნა multipart/form-data უნდა იყოს (JSON-ით ფაილი არ იგზავნება).
    """

    serializer_class = ProductCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # არასწორი მონაცემები: 400 + შეცდომები ველების მიხედვით
        # მფლობელს კლიენტისგან არ ვიღებთ: ვწერთ ავტორიზებულ მომხმარებელს
        product = serializer.save(user=request.user)

        # პასუხად სრული ინფორმაცია (id-ითა და ჩადგმული კატეგორიით), არა მხოლოდ გამოგზავნილი ველები
        data = ProductDetailSerializer(product, context=self.get_serializer_context()).data
        headers = {"Location": reverse("api:product-detail", args=[product.pk], request=request)}
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)
