from rest_framework import serializers
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import AccountabilityPartner
from users.serializers import UserSerializer

User = get_user_model()

class AccountabilityPartnerSerializer(serializers.ModelSerializer):
    requester = UserSerializer(read_only=True)
    partner = UserSerializer(read_only=True)
    partner_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = AccountabilityPartner
        fields = ['id', 'requester', 'partner', 'partner_id', 'status', 'created_at']
        read_only_fields = ['status']

    def create(self, validated_data):
        partner_id = validated_data.pop('partner_id')
        requester = self.context['request'].user
        try:
            partner = User.objects.get(id=partner_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("Partner not found.")
        
        # Check if a request already exists
        if AccountabilityPartner.objects.filter(requester=requester, partner=partner).exists():
            raise serializers.ValidationError("Accountability partner request already sent.")

        accountability_partner = AccountabilityPartner.objects.create(requester=requester, partner=partner, **validated_data)
        return accountability_partner
