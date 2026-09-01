from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def elevate_admin_role(sender, instance, created, **kwargs):
    if created and getattr(instance, "role", None) == "admin":
        changed = False
        if not instance.is_staff:
            instance.is_staff = True
            changed = True
        if not instance.is_superuser:
            instance.is_superuser = True
            changed = True
        if changed:
            instance.save(update_fields=["is_staff", "is_superuser"])
