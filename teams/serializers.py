from rest_framework import serializers
from .models import Team, TeamMembership
from users.serializers import UserSerializer
from organizations.models import Organization
from django.contrib.auth import get_user_model

User = get_user_model()

class LimitedTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name']

class TeamMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = TeamMembership
        fields = ['id', 'user', 'user_id', 'role', 'joined_at', 'team']
        read_only_fields = ['joined_at', 'team']

class TeamSerializer(serializers.ModelSerializer):
    memberships = TeamMembershipSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), source='organization', write_only=True
    )

    class Meta:
        model = Team
        fields = ['id', 'name', 'organization', 'organization_id', 'created_by', 'created_at', 'updated_at', 'memberships']
        read_only_fields = ['organization', 'created_by', 'created_at', 'updated_at']

    def validate(self, data):
        if self.instance is None and 'organization' not in data:
            raise serializers.ValidationError({"organization_id": "This field is required for creating a team."})
        return data
