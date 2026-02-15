from django.contrib import admin
from .models import Task, TaskComment, TaskAttachment

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'assignee', 'status', 'due_date']
    search_fields = ['title', 'owner__username']