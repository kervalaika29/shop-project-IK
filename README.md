# Mini Shop — Django Homework 36

Django პროექტი პროდუქტებითა და კატეგორიებით (ბაზა: **sqlite3**).

## გაშვება (Windows)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

ბაზა (`db.sqlite3`) უკვე შევსებულია: 5 კატეგორია, 14 პროდუქტი.
თუ ბაზა თავიდან გინდათ შევსება:

```
python manage.py migrate
python manage.py loaddata initial_data
```

ადმინისტრატორის შესაქმნელად: `python manage.py createsuperuser` (მისამართი: `/admin/`).

## გვერდები

| მისამართი | აღწერა |
|---|---|
| `/` | მთავარი: ყველა პროდუქტი ფასის ზრდადობით + კატეგორიების სია (რაოდენობა ფრჩხილებში) |
| `/category/<id>/` | კონკრეტული კატეგორიის პროდუქტები |
| `/sale/` | ფასდაკლებული პროდუქტები |
| `/product/<id>/` | პროდუქტის დეტალური გვერდი |

## მოდელები

- `Category` — `name`, `description`
- `Product` — `name`, `description`, `price`, `category` (**ForeignKey** → Category), `has_discount` (ფასდაკლება აქვს თუ არა)

## ტესტები

```
python manage.py test shop
```
