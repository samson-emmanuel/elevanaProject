from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Organization, Membership

User = get_user_model()

class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    role = serializers.ChoiceField(choices=[('employee', 'Employee'), ('manager', 'Manager'), ('admin', 'Admin')])

class LimitedUserSerializer(serializers.ModelSerializer):
    """A lightweight serializer for user info to avoid circular imports."""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'logo', 'created_at', 'stripe_customer_id', 'is_premium', 'is_on_trial', 'trial_ends_at']
        read_only_fields = ['created_at', 'stripe_customer_id', 'is_premium', 'is_on_trial', 'trial_ends_at']

    def create(self, validated_data):
        from django.utils import timezone
        from datetime import timedelta

        organization = Organization.objects.create(**validated_data)
        organization.is_on_trial = True
        organization.trial_start_date = timezone.now()
        organization.trial_ends_at = timezone.now() + timedelta(days=7)
        organization.save()
        return organization

class MembershipSerializer(serializers.ModelSerializer):
    user = LimitedUserSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    organization_id = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), source='organization', write_only=True
    )
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = Membership
        fields = ['id', 'user', 'user_id', 'organization', 'organization_id', 'role', 'joined_at']
        read_only_fields = ['joined_at']
