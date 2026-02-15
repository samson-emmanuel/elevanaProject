from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import AccountabilityPartner
from .serializers import AccountabilityPartnerSerializer

class AccountabilityPartnerViewSet(viewsets.ModelViewSet):
    serializer_class = AccountabilityPartnerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AccountabilityPartner.objects.filter(requester=self.request.user) | AccountabilityPartner.objects.filter(partner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(requester=self.request.user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        accountability_request = self.get_object()
        if accountability_request.partner != request.user:
            return Response({'error': 'You are not authorized to accept this request.'}, status=status.HTTP_403_FORBIDDEN)

        accountability_request.status = 'accepted'
        accountability_request.save()
        return Response({'status': 'Request accepted.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        accountability_request = self.get_object()
        if accountability_request.partner != request.user:
            return Response({'error': 'You are not authorized to reject this request.'}, status=status.HTTP_403_FORBIDDEN)

        accountability_request.status = 'rejected'
        accountability_request.save()
        return Response({'status': 'Request rejected.'})