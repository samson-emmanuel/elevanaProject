from celery import shared_task
from django.utils import timezone
from .models import User
from organizations.models import Organization

@shared_task
def check_expired_trials():
    """
    A Celery task to check for expired trials for both users and organizations.
    """
    now = timezone.now()
    
    # Check for expired user trials
    expired_user_trials = User.objects.filter(
        is_on_trial=True,
        trial_ends_at__lt=now
    )
    for user in expired_user_trials:
        user.is_on_trial = False
        user.is_premium = False
        user.save()

    # Check for expired organization trials
    expired_org_trials = Organization.objects.filter(
        is_on_trial=True,
        trial_ends_at__lt=now
    )
    for org in expired_org_trials:
        org.is_on_trial = False
        org.is_premium = False
        org.save()

    return f"Checked for expired trials. Deactivated {expired_user_trials.count()} user trials and {expired_org_trials.count()} organization trials."
