from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, CustomerProfile, SellerProfile

@receiver(post_save, sender=User)
def create_profiles(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.role == User.Roles.SELLER:
        SellerProfile.objects.create(user=instance)
    else:
        CustomerProfile.objects.create(user=instance)
