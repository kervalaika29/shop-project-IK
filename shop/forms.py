from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db.models.functions import Lower

from .models import Category, Product

# სურათის მაქსიმალური ზომა (5 MB) და დაშვებული ფორმატები
MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class ProductForm(forms.ModelForm):
    """
    პროდუქტის დამატებისა და რედაქტირების ფორმა.
    ერთი და იგივე ფორმა გამოიყენება ორივე შემთხვევაში: დამატებისას ცარიელია,
    რედაქტირებისას კი არსებული პროდუქტის მონაცემებით ივსება (instance=product).

    user ველი ფორმაში განზრახ არ არის: მფლობელს მომხმარებელი ფორმიდან კი არ ირჩევს,
    view-ში ავტომატურად ვწერთ იმ მომხმარებელს, ვინც ამ მომენტში შესულია სისტემაში.
    """

    class Meta:
        model = Product
        fields = ["name", "category", "price", "image", "description", "has_discount"]
        labels = {
            "name": "Product name",
            "category": "Category",
            "price": "Price (₾)",
            "image": "Product image",
            "description": "Description",
            "has_discount": "This product is on sale (discount)",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Lenovo IdeaPad 3"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01", "placeholder": "0.00"}),
            # ClearableFileInput: რედაქტირებისას აჩვენებს მიმდინარე სურათს და "Clear" ღილაკს
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Short description (optional)"}),
            "has_discount": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # select-ის პირველი (ცარიელი) ვარიანტის ტექსტი
        self.fields["category"].empty_label = "— Select a category —"

    def clean_name(self):
        """სახელი: ზედმეტი გამოტოვებები იჭრება და მინიმუმ 2 სიმბოლო უნდა იყოს."""
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise ValidationError("Product name must contain at least 2 characters.")
        return name

    def clean_price(self):
        """ფასი ნულზე მეტი უნდა იყოს."""
        price = self.cleaned_data["price"]
        if price <= 0:
            raise ValidationError("Price must be greater than zero.")
        return price

    def clean_image(self):
        """
        სურათის შემოწმება. ImageField თვითონ ამოწმებს, რომ ფაილი მართლა სურათია (Pillow-ით).
        აქ ვამატებთ ფორმატისა და ზომის შეზღუდვას. შემოწმება მხოლოდ ახლად ატვირთულ
        ფაილზე ხდება (UploadedFile): არსებული სურათი ან "Clear" (False) ამას არ სჭირდება.
        """
        image = self.cleaned_data.get("image")
        if isinstance(image, UploadedFile):
            if image.content_type not in ALLOWED_IMAGE_TYPES:
                raise ValidationError("Please upload a JPG, PNG, GIF or WEBP image.")
            if image.size > MAX_IMAGE_SIZE:
                raise ValidationError("The image is too large (maximum size is 5 MB).")
        return image


# ---------------------------------------------------------------------------
# HW43: ძებნა, ფილტრაცია და სორტირება
# ---------------------------------------------------------------------------

# სორტირების ვარიანტები: ?sort=<გასაღები>. თითოეულს აქვს: ტექსტი ღილაკზე, ტექსტი
# სათაურში ("Sorted by ...") და ის ველები, რომლებითაც order_by აწყობს პროდუქტებს.
#
# ორი დეტალი:
# - ბოლოს ყოველთვის "pk" არის. თუ ორ პროდუქტს ერთნაირი ფასი ან სახელი აქვს, მათი რიგი
#   მაინც ყოველთვის ერთნაირია, ამიტომ პაგინაციისას პროდუქტი გვერდებს შორის არ იკარგება
#   და არ მეორდება.
# - Lower("name"): სახელებს დიდი/პატარა ასოს გარეშე ვადარებთ, ამიტომ "apple" "Zebra"-ს
#   წინ დგას (მარტივი order_by("name") დიდ ასოებს ყველა პატარა ასოს წინ დააყენებდა).
SORT_OPTIONS = {
    "price_asc": ("Price: low to high", "price, low to high", ("price", "pk")),
    "price_desc": ("Price: high to low", "price, high to low", ("-price", "pk")),
    "name_asc": ("Name: A to Z", "name, A to Z", (Lower("name"), "pk")),
    "name_desc": ("Name: Z to A", "name, Z to A", (Lower("name").desc(), "pk")),
    "newest": ("Newest first", "newest first", ("-pk",)),
}
DEFAULT_SORT = "price_asc"  # ძველი ქცევა: ფასის ზრდადობით

# ფილტრის ველები (sort აქ არ არის: ის ფილტრი კი არა, რიგია)
FILTER_FIELDS = ("q", "category", "min_price", "max_price", "sale")


class ProductFilterForm(forms.Form):
    """
    პროდუქტების ძებნის, ფილტრაციისა და სორტირების ფორმა (HW43).

    ეს ფორმა მონაცემებს POST-ით კი არა, მისამართიდან (GET, ?q=...&min_price=...) იღებს და
    არაფერს ინახავს: მისი მიზანია მხოლოდ მისამართის პარამეტრების შემოწმება. ასე ბრაუზერში
    ძებნის შედეგი ბმულადაც ინახება და გვერდები (?page=2) მას არ კარგავს.

    ველები (ყველა არასავალდებულოა; სამივე ფუნქცია ერთ ფორმაშია, ამიტომ ერთად მუშაობს):
    - q          ძებნა: პროდუქტის სახელში ან აღწერაში,
    - category   ფილტრი: კატეგორია,
    - min_price / max_price  ფილტრი: ფასის ზღვარი,
    - sale       ფილტრი: მხოლოდ ფასდაკლებული პროდუქტები,
    - sort       სორტირება (SORT_OPTIONS-ის ერთ-ერთი გასაღები).

    არასწორი მნიშვნელობა (მაგ. ?min_price=abc) საიტს არ აფუჭებს: ის ველი უბრალოდ გამოტოვდება
    (cleaned_data-ში არ მოხვდება), დანარჩენი ფილტრები კი ისევ მუშაობს და ფორმა აჩვენებს, რა იყო არასწორი.
    """

    q = forms.CharField(
        label="Search",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control text-dark", "placeholder": "Search by name or description"}),
    )
    category = forms.ModelChoiceField(
        label="Category",
        queryset=Category.objects.all(),  # view-ში ვცვლით: მხოლოდ არაცარიელი კატეგორიები
        required=False,
        empty_label="All categories",
        widget=forms.Select(attrs={"class": "form-select text-dark"}),
    )
    # max_digits/decimal_places Product.price-ის იგივეა (10 და 2): ძალიან დიდი რიცხვი
    # (მაგ. 1e30) ბაზას არ მიაღწევს, ფორმა მას შეცდომად დაითვლის და გამოტოვებს
    min_price = forms.DecimalField(
        label="Min price (₾)",
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control text-dark", "min": "0", "step": "0.01", "placeholder": "0"}),
    )
    max_price = forms.DecimalField(
        label="Max price (₾)",
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control text-dark", "min": "0", "step": "0.01", "placeholder": "Any"}),
    )
    sale = forms.BooleanField(
        label="On sale only",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    sort = forms.ChoiceField(
        label="Sort",
        required=False,
        choices=[(key, option[0]) for key, option in SORT_OPTIONS.items()],
    )

    def __init__(self, *args, fixed=(), **kwargs):
        """
        fixed: ველები, რომლებიც ამ გვერდზე უკვე დაფიქსირებულია და ფორმაში არ უნდა იყოს.
        მაგ. კატეგორიის გვერდზე "category" (იქ კატეგორია უკვე არჩეულია), sale-ის გვერდზე "sale".
        """
        super().__init__(*args, **kwargs)
        for name in fixed:
            del self.fields[name]

    def clean(self):
        """ფასის ზღვრები ერთმანეთს არ უნდა ეწინააღმდეგებოდეს: min არ უნდა აღემატებოდეს max-ს."""
        cleaned_data = super().clean()
        min_price = cleaned_data.get("min_price")
        max_price = cleaned_data.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            # add_error ველს cleaned_data-იდანაც ხსნის: max_price გამოტოვდება, min_price კი იმუშავებს
            self.add_error("max_price", "Max price must not be lower than min price (max price was ignored).")
        return cleaned_data
