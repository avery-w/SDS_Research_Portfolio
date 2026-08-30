from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, BooleanField, SubmitField,
                     TextAreaField, SelectField, IntegerField, FloatField,
                     MultipleFileField)
from wtforms.validators import (DataRequired, Email, Length, EqualTo,
                                ValidationError, NumberRange, Optional)
from app.models import User, Category


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    role = SelectField('I want to', choices=[
        ('customer', 'Shop as a Customer'),
        ('seller', 'Sell as a Seller')
    ], default='customer')
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email already registered.')


class StoreForm(FlaskForm):
    name = StringField('Store Name', validators=[DataRequired(), Length(max=128)])
    description = TextAreaField('Description', validators=[Length(max=2000)])
    logo = FileField('Logo Image', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'])])
    banner = FileField('Banner Image', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'])])
    submit = SubmitField('Save Store')


class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=256)])
    description = TextAreaField('Description', validators=[Length(max=5000)])
    price = FloatField('Price ($)', validators=[DataRequired(), NumberRange(min=0.01)])
    compare_at_price = FloatField('Compare at Price ($)', validators=[Optional(), NumberRange(min=0)])
    sku = StringField('SKU', validators=[Optional(), Length(max=64)])
    quantity = IntegerField('Quantity in Stock', validators=[DataRequired(), NumberRange(min=0)])
    weight = FloatField('Weight', validators=[Optional(), NumberRange(min=0)])
    weight_unit = SelectField('Weight Unit', choices=[
        ('lb', 'Pounds (lb)'), ('oz', 'Ounces (oz)'),
        ('kg', 'Kilograms (kg)'), ('g', 'Grams (g)')
    ], default='lb')
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    image = FileField('Main Image', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'])])
    additional_images = MultipleFileField('Additional Images',
                                          validators=[FileAllowed(['jpg', 'jpeg', 'png', 'webp'])])
    tags = StringField('Tags (comma separated)', validators=[Optional(), Length(max=512)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Product')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_id.choices = [(0, '-- No Category --')] + [
            (c.id, c.name) for c in Category.query.filter_by(is_active=True).order_by(Category.name).all()
        ]


class CartAddForm(FlaskForm):
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1, max=99)], default=1)
    submit = SubmitField('Add to Cart')


class CheckoutForm(FlaskForm):
    shipping_address = StringField('Street Address', validators=[DataRequired(), Length(max=256)])
    shipping_city = StringField('City', validators=[DataRequired(), Length(max=64)])
    shipping_state = StringField('State', validators=[DataRequired(), Length(max=64)])
    shipping_zip = StringField('ZIP Code', validators=[DataRequired(), Length(max=20)])
    shipping_country = SelectField('Country', choices=[('US', 'United States')], default='US')
    shipping_method = SelectField('Shipping Method', choices=[
        ('standard', 'Standard (5-7 business days)'),
        ('expedited', 'Expedited (2-3 business days)'),
        ('overnight', 'Overnight (1 business day)')
    ])
    payment_method = SelectField('Payment Method', choices=[
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal')
    ])
    notes = TextAreaField('Order Notes (optional)', validators=[Length(max=500)])
    submit = SubmitField('Place Order')


class ReturnRequestForm(FlaskForm):
    reason = SelectField('Reason for Return', choices=[
        ('defective', 'Defective/Damaged Item'),
        ('wrong_item', 'Wrong Item Received'),
        ('not_as_described', 'Not As Described'),
        ('changed_mind', 'Changed Mind'),
        ('arrived_late', 'Arrived Too Late'),
        ('other', 'Other')
    ])
    description = TextAreaField('Additional Details', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Submit Return Request')


class MessageForm(FlaskForm):
    content = TextAreaField('Message', validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField('Send Message')


class UserProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address = StringField('Address', validators=[Optional(), Length(max=256)])
    city = StringField('City', validators=[Optional(), Length(max=64)])
    state = StringField('State', validators=[Optional(), Length(max=64)])
    zip_code = StringField('ZIP Code', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Update Profile')


class AdminUserForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[
        ('customer', 'Customer'),
        ('seller', 'Seller'),
        ('admin', 'Admin')
    ])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save User')


class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=64)])
    description = StringField('Description', validators=[Optional(), Length(max=256)])
    icon = StringField('Icon Class', validators=[Optional(), Length(max=64)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Category')


class PlatformSettingsForm(FlaskForm):
    platform_name = StringField('Platform Name', validators=[DataRequired(), Length(max=64)])
    shipping_base_rate = FloatField('Base Shipping Rate ($)', validators=[NumberRange(min=0)])
    free_shipping_threshold = FloatField('Free Shipping Threshold ($)', validators=[NumberRange(min=0)])
    tax_rate = FloatField('Tax Rate (%)', validators=[NumberRange(min=0, max=100)])
    platform_fee_percent = FloatField('Platform Fee (%)', validators=[NumberRange(min=0, max=100)])
    support_email = StringField('Support Email', validators=[Email()])
    submit = SubmitField('Save Settings')


class ShippingRateForm(FlaskForm):
    weight = FloatField('Package Weight (lb)', validators=[DataRequired(), NumberRange(min=0.1)])
    length = FloatField('Length (in)', validators=[Optional(), NumberRange(min=0)])
    width = FloatField('Width (in)', validators=[Optional(), NumberRange(min=0)])
    height = FloatField('Height (in)', validators=[Optional(), NumberRange(min=0)])
    destination_zip = StringField('Destination ZIP Code', validators=[DataRequired(), Length(max=20)])
    destination_city = StringField('Destination City', validators=[Optional(), Length(max=64)])
    destination_state = StringField('Destination State', validators=[Optional(), Length(max=64)])
    service = SelectField('Service', choices=[
        ('ground', 'UPS Ground'),
        ('3day', 'UPS 3 Day Select'),
        ('2day', 'UPS 2nd Day Air'),
        ('nextday', 'UPS Next Day Air'),
        ('saver', 'UPS Saver')
    ], default='ground')
    submit = SubmitField('Calculate Rate')


class OrderStatusForm(FlaskForm):
    status = SelectField('Order Status', choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ])
    tracking_number = StringField('Tracking Number', validators=[Optional(), Length(max=128)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Update Status')
