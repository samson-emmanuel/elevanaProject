from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Task, TaskAttachment, TaskComment
from users.serializers import UserSerializer
from accountability.models import TaskAccountability
from teams.models import Team
from teams.serializers import LimitedTeamSerializer

User = get_user_model()

class TaskCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'author', 'text', 'created_at', 'task']
        read_only_fields = ['author', 'created_at', 'task']

class TaskSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    assignee = UserSerializer(read_only=True)
    team = LimitedTeamSerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='assignee', write_only=True, required=False, allow_null=True
    )
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), source='team', write_only=True, required=False, allow_null=True
    )
    attachment_file = serializers.FileField(write_only=True, required=False)
    accountability_partners = serializers.ListField(
        child=serializers.EmailField(), write_only=True, required=False
    )
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['owner', 'completed_at']

    def get_can_edit(self, obj):
        user = self.context['request'].user
        # Check if the user is the task owner or an admin/manager in the task's organization
        if not user.is_authenticated:
            return False
        if obj.owner == user:
            return True
        if obj.organization is None:
            return False
        return user.membership_set.filter(
            organization=obj.organization, role__in=['admin', 'manager']
        ).exists()

    def validate_attachment_file(self, value):
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
        ALLOWED_MIME_TYPES = [
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/svg+xml',
            'application/pdf',
            'text/plain'
        ]

        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError("File size too large. Maximum size is 5MB.")
        
        if value.content_type not in ALLOWED_MIME_TYPES:
            raise serializers.ValidationError("Unsupported file type. Allowed types are JPG, PNG, GIF, SVG, PDF, and TXT.")
        
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        attachment_file = validated_data.pop('attachment_file', None)
        partner_emails = validated_data.pop('accountability_partners', [])

        # Enforce limit for non-premium users
        if not user.has_premium_access and len(partner_emails) > 1:
            raise serializers.ValidationError("Free users can only add one accountability partner per task.")

        validated_data['owner'] = user
        task = super().create(validated_data)

        if attachment_file:
            TaskAttachment.objects.create(
                task=task,
                file=attachment_file,
                uploaded_by=user
            )
        
        if partner_emails:
            for email in partner_emails:
                try:
                    partner_user = User.objects.get(email=email)
                    TaskAccountability.objects.create(task=task, partner=partner_user)
                except User.DoesNotExist:
                    # Silently ignore if a user with the email doesn't exist
                    pass
        
        return task

    def update(self, instance, validated_data):
        user = self.context['request'].user
        partner_emails = validated_data.pop('accountability_partners', None)

        if partner_emails is not None:
            # Enforce limit for non-premium users
            if not user.has_premium_access and len(partner_emails) > 1:
                raise serializers.ValidationError("Free users can only add one accountability partner per task.")

            # Full replacement of accountability partners on update
            instance.accountability_partnerships.all().delete()
            for email in partner_emails:
                try:
                    partner_user = User.objects.get(email=email)
                    TaskAccountability.objects.create(task=instance, partner=partner_user)
                except User.DoesNotExist:
                    pass
        
        return super().update(instance, validated_data)