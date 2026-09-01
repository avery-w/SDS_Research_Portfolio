from django.core.exceptions import ValidationError
def validate_image_file(f):
    ct = getattr(f, 'content_type', '')
    if ct not in ('image/jpeg','image/png','image/webp'):
        raise ValidationError('Unsupported image type.')
    if f.size > 5 * 1024 * 1024:
        raise ValidationError('Image too large.')
