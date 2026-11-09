"""
სერიალიზატორები (HW45).

სერიალიზატორი Django-ს მოდელის ობიექტს JSON-ად გადაცვლის (პასუხი) და პირიქით: მომხმარებლის
გამოგზავნილ JSON-ს ამოწმებს და ობიექტად აქცევს (მოთხოვნა). ყოველი endpoint-ისთვის ცალკე,
სწორედ მისთვის შესაფერისი სერიალიზატორია:

    სია (კატეგორიები)  -> CategoryListSerializer     (+ product_count)
    სია (პროდუქტები)   -> ProductListSerializer      (მოკლე ინფორმაცია)
    დეტალები           -> ProductDetailSerializer    (სრული ინფორმაცია, კატეგორია ჩადგმულია)
    შექმნა             -> ProductCreateSerializer    (მხოლოდ ის ველები, რომლებსაც მომხმარებელი წერს)
"""

from rest_framework import serializers

from shop import forms as shop_forms
from shop.models import Category, Product


def absolute_image_url(product, request):
    """
    სურათის სრული მისამართი (http://127.0.0.1:8000/media/products/...). ზუსტად იმავე სურათს
    აბრუნებს, რასაც საიტი აჩვენებს (Product.image_url): ატვირთულს, ან თუ პროდუქტს სურათი არ
    აქვს, შაბლონის მზა სურათს. API-ს გარედან იყენებენ, ამიტომ მისამართი სრული უნდა იყოს
    და არა "/media/...".
    """
    url = product.image_url
    return request.build_absolute_uri(url) if request is not None else url


# ---------------------------------------------------------------------------
# კატეგორიები
# ---------------------------------------------------------------------------

class CategorySerializer(serializers.ModelSerializer):
    """კატეგორიის ძირითადი ველები. პროდუქტის დეტალებში ჩადგმული სახითაც გამოიყენება."""

    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class CategoryListSerializer(CategorySerializer):
    """
    კატეგორიების სიისთვის: იგივე ველები + რამდენი პროდუქტია კატეგორიაში. product_count
    ბაზიდან მოდის (view-ში annotate(Count)), ამიტომ ყოველი კატეგორიისთვის ცალკე მოთხოვნა არ გვჭირდება.
    """

    product_count = serializers.IntegerField(read_only=True)

    class Meta(CategorySerializer.Meta):
        fields = [*CategorySerializer.Meta.fields, "product_count"]


# ---------------------------------------------------------------------------
# პროდუქტები: წაკითხვა
# ---------------------------------------------------------------------------

class ProductListSerializer(serializers.ModelSerializer):
    """
    პროდუქტების სიისთვის: მოკლე ინფორმაცია (აღწერა და მფლობელი არ არის, რომ სია მსუბუქი იყოს).
    url არის ამ პროდუქტის დეტალური API-ს მისამართი, რომლითაც კლიენტი სრულ ინფორმაციაზე გადადის.
    """

    url = serializers.HyperlinkedIdentityField(view_name="api:product-detail")
    category_name = serializers.CharField(source="category.name", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "url", "name", "price", "has_discount", "category", "category_name", "image"]
        read_only_fields = fields

    def get_image(self, product):
        return absolute_image_url(product, self.context.get("request"))


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    პროდუქტის სრული ინფორმაცია: აღწერა, კატეგორია მთლიანი ობიექტით (ჩადგმული CategorySerializer)
    და მფლობელი (მომხმარებლის სახელი). 14 ძველ პროდუქტს მფლობელი არ ჰყავს (HW41-მდე დაემატა),
    მათთვის owner არის null.
    """

    category = CategorySerializer(read_only=True)
    owner = serializers.CharField(source="user.username", read_only=True, default=None)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "has_discount", "image", "category", "owner"]
        read_only_fields = fields

    def get_image(self, product):
        return absolute_image_url(product, self.context.get("request"))


# ---------------------------------------------------------------------------
# პროდუქტები: შექმნა
# ---------------------------------------------------------------------------

class ProductCreateSerializer(serializers.ModelSerializer):
    """
    პროდუქტის შესაქმნელად მოსული მონაცემების შემოწმება. წესები იგივეა, რაც საიტის ფორმაშია
    (shop.forms.ProductForm), ამიტომ API-დან და საიტიდან დამატებული პროდუქტი ერთნაირ წესებს იცავს.

    user ველი აქ განზრახ არ არის: მფლობელს კლიენტი არ ირჩევს, view ჩაწერს იმ მომხმარებელს, ვინც
    ახლა ავტორიზებულია. ამიტომ ხელით გამოგზავნილი "user": 5 უბრალოდ იგნორირდება (როგორც ფორმაში).

    category ველში კატეგორიის id იწერება (მაგ. "category": 2); არარსებული id შეცდომას აბრუნებს.
    """

    class Meta:
        model = Product
        fields = ["name", "description", "price", "category", "has_discount", "image"]

    def validate_name(self, value):
        """სახელი (ზედმეტი გამოტოვებები უკვე მოჭრილია): მინიმუმ 2 სიმბოლო."""
        if len(value) < 2:
            raise serializers.ValidationError("Product name must contain at least 2 characters.")
        return value

    def validate_price(self, value):
        """ფასი ნულზე მეტი უნდა იყოს."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_image(self, image):
        """
        სურათი: ImageField თვითონ ამოწმებს, რომ ფაილი მართლა სურათია (Pillow-ით, ფორმატს ფაილის
        შიგთავსიდან ადგენს და არა სახელიდან). აქ ვამატებთ საიტის იგივე შეზღუდვას: ფორმატი
        JPG/PNG/GIF/WEBP და მაქსიმუმ 5 MB. ლიმიტებს shop.forms-იდან ვკითხულობთ, ერთ ადგილას წერია.
        """
        if image.content_type not in shop_forms.ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError("Please upload a JPG, PNG, GIF or WEBP image.")
        if image.size > shop_forms.MAX_IMAGE_SIZE:
            raise serializers.ValidationError("The image is too large (maximum size is 5 MB).")
        return image
