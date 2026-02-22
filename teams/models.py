from django.db import models
from django.conf import settings
from organizations.models import Organization

User = settings.AUTH_USER_MODEL

class Team(models.Model):
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='teams')        
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_teams')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'organization')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

class TeamMembership(models.Model):
    ROLE_CHOICES = (
        ('manager', 'Manager'),
        ('assistant', 'Assistant'),
        ('member', 'Member'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'team')
        ordering = ['user__first_name', 'user__last_name']

    def __str__(self):
        return f"{self.user.get_full_name() if self.user.first_name else self.user.email} - {self.role} in {self.team.name}"
