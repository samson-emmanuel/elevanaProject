from django.db.models.signals import post_save
from django.dispatch import receiver

from accountability import apps
from .models import Task
from accountability.models import AccountabilityPartner

@receiver(post_save, sender=Task)
def auto_add_manager_as_partner(sender, instance, created, **kwargs):
    if created and instance.assignee and instance.owner != instance.assignee:
        # Find if owner is manager/admin in same org
        Membership = apps.get_model('organizations', 'Membership')
        owner_membership = Membership.objects.filter(user=instance.owner, organization=instance.organization).first()
        if owner_membership and owner_membership.role in ['manager', 'admin']:
            AccountabilityPartner.objects.get_or_create(
                requester=instance.assignee,
                partner=instance.owner,
                defaults={'status': 'accepted'}
            )