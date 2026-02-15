from django.db import models
from users.models import User
from tasks.models import Task


class AccountabilityPartner(models.Model):
    requester = models.ForeignKey(User, related_name='requested_partners', on_delete=models.CASCADE)
    partner = models.ForeignKey(User, related_name='accountability_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('pending','Pending'),('accepted','Accepted'),('rejected','Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('requester', 'partner')


class TaskAccountability(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='accountability_partnerships')
    partner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accountable_tasks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('task', 'partner')
        verbose_name = 'Task Accountability'
        verbose_name_plural = 'Task Accountabilities'