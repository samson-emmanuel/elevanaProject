from django.contrib.auth.models import AbstractUser
from django.db import models
from sorl.thumbnail import ImageField, get_thumbnail

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    avatar = ImageField(upload_to='avatars/', blank=True, null=True)
    is_premium = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
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


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def get_avatar_40(self):
        if self.avatar:
            return get_thumbnail(self.avatar, '40x40', crop='center', quality=99).url
        return "/static/default-avatar-40.png"

    def get_avatar_100(self):
        if self.avatar:
            return get_thumbnail(self.avatar, '100x100', crop='center', quality=99).url
        return "/static/default-avatar-100.png"

    def get_avatar_400(self):
        if self.avatar:
            return get_thumbnail(self.avatar, '400x400', crop='center', quality=99).url
        return "/static/default-avatar-400.png" 