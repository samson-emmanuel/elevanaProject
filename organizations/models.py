from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Organization(models.Model):
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='org_logos/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    is_premium = models.BooleanField(default=False)
    trial_start_date = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    is_on_trial = models.BooleanField(default=False)

    @property
    def is_trial_active(self):
        from django.utils import timezone
        if self.is_on_trial and self.trial_ends_at:
            return self.trial_ends_at > timezone.now()
        return False

    @property
    def has_premium_access(self):
        return self.is_premium or self.is_trial_active

    def __str__(self):
        return self.name

class Membership(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('employee', 'Employee'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'organization')
