from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Product


@receiver(post_save, sender=Product)
def print_product_updated(sender, instance, created, **kwargs):
    """
    პროდუქტის განახლებისას ტერმინალში (იქ, სადაც runserver გაშვებულია) ბეჭდავს:
        Product "Asus Laptop" was updated.

    post_save ყოველი .save()-ის შემდეგ სრულდება. created=True ნიშნავს, რომ პროდუქტი ახლა
    შეიქმნა (ახალი ჩანაწერი), ამიტომ მას "updated" არ ვწერთ: ვბეჭდავთ მხოლოდ მაშინ,
    როცა უკვე არსებული პროდუქტი შეინახა (საიტიდან Edit-ით, admin-იდან ან კოდიდან).
    signal თავისით მუშაობს, view-ებში ან admin-ში არაფერი უნდა შეიცვალოს.
    """
    if not created:
        print(f'Product "{instance.name}" was updated.', flush=True)


@receiver(post_delete, sender=Product)
def delete_image_file_with_product(sender, instance, **kwargs):
    """
    პროდუქტის წაშლისას მისი სურათის ფაილიც იშლება დისკიდან, რომ media/ საქაღალდეში
    გამოუყენებელი ფაილები არ დაგროვდეს. signal იმ შემთხვევაშიც მუშაობს, როცა პროდუქტი
    სხვა ობიექტთან ერთად იშლება (მაგ. კატეგორიის ან მომხმარებლის წაშლისას, CASCADE).
    """
    if instance.image:
        instance.image.delete(save=False)


@receiver(pre_save, sender=Product)
def delete_replaced_image_file(sender, instance, raw=False, **kwargs):
    """
    განახლებისას სურათი შეიცვალა ან წაიშალა ("Clear")? მაშინ ძველი ფაილი იშლება.
    raw=True fixture-ის (loaddata) ჩატვირთვაა, მაშინ არაფერს ვუშვებთ.
    """
    if raw or instance.pk is None:
        return
    old = Product.objects.filter(pk=instance.pk).only("image").first()
    if old and old.image and old.image.name != instance.image.name:
        old.image.delete(save=False)
