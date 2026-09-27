from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Product, ProductImage, Store, User
from .shipping import SERVICES

US_STATES = sorted(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND "
    "OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
)


class SignupForm(UserCreationForm):
    role = forms.ChoiceField(choices=[(User.Role.CUSTOMER, "Customer"), (User.Role.SELLER, "Seller")])

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "role"]

    def __init__(self, *args, allow_sellers=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not allow_sellers:
            self.fields["role"].choices = [(User.Role.CUSTOMER, "Customer")]


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ["name", "description"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "description", "price", "stock", "weight_lb", "length_in", "width_in", "height_in", "is_active"]


class ImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image"]


class AddressForm(forms.Form):
    name = forms.CharField(max_length=120)
    line1 = forms.CharField(max_length=200, label="Street address")
    city = forms.CharField(max_length=100)
    state = forms.ChoiceField(choices=[(s, s) for s in US_STATES])
    zip = forms.RegexField(regex=r"^\d{5}(-\d{4})?$", max_length=10, label="ZIP")


class CheckoutForm(AddressForm):
    service = forms.ChoiceField(choices=list(SERVICES.items()))


class ShipForm(forms.Form):
    tracking_number = forms.RegexField(regex=r"^[A-Za-z0-9]{6,40}$")


class ReturnForm(forms.Form):
    return_reason = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 4}))


class MessageForm(forms.Form):
    body = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 3}), label="Message")
