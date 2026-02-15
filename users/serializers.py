from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from sorl.thumbnail import get_thumbnail
from organizations.serializers import MembershipSerializer


User = get_user_model()

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming a password reset attempt.
    """
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("The two password fields didn't match.")
        return attrs

    def save(self):
        uidb64 = self.validated_data['uid']
        token = self.validated_data['token']
        new_password = self.validated_data['new_password']

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            return user
        raise serializers.ValidationError('Invalid token or user ID.')

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'address', 'avatar']


class UserSerializer(serializers.ModelSerializer):
    avatar_40 = serializers.SerializerMethodField()
    avatar_100 = serializers.SerializerMethodField()
    avatar_400 = serializers.SerializerMethodField()
    has_premium_access = serializers.ReadOnlyField()
    is_on_trial = serializers.ReadOnlyField()
    trial_ends_at = serializers.ReadOnlyField()
    memberships = MembershipSerializer(source='membership_set', many=True, read_only=True)
    subscription_ends_at = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'phone_number', 'address', 'avatar', 'avatar_40', 
                  'avatar_100', 'avatar_400', 'has_premium_access', 'is_on_trial', 
                  'trial_ends_at', 'date_joined', 'memberships', 'subscription_ends_at']
        extra_kwargs = {'password': {'write_only': True}}

    def get_subscription_ends_at(self, obj):
        if hasattr(obj, 'subscription') and obj.subscription:
            return obj.subscription.current_period_end
        return None

    def get_avatar_40(self, obj):
        return obj.get_avatar_40()

    def get_avatar_100(self, obj):
        return obj.get_avatar_100()

    def get_avatar_400(self, obj):
        return obj.get_avatar_400()

    def create(self, validated_data):
        from django.utils import timezone
        from datetime import timedelta

        user = User.objects.create_user(**validated_data)
        user.is_on_trial = True
        user.trial_start_date = timezone.now()
        user.trial_ends_at = timezone.now() + timedelta(days=7)
        user.save()
        return user