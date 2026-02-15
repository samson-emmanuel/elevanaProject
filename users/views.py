import logging
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.core.mail import send_mail
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)

from rest_framework import viewsets, status, mixins, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserUpdateSerializer, PasswordResetConfirmSerializer

User = get_user_model()

class UserViewSet(mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=['get', 'put', 'patch', 'post'], url_path='me')
    def me(self, request, *args, **kwargs):
        instance = self.request.user
        if request.method == 'GET':
            print(f"User {instance.email} is premium: {instance.is_premium}")
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        
        if request.method == 'POST':
            from django.utils import timezone
            from datetime import timedelta

            logger.info(f"User {instance.email} attempting to start trial.")
            logger.info(f"is_premium: {instance.is_premium}")
            logger.info(f"is_trial_active: {instance.is_trial_active}")

            if instance.is_premium or instance.is_trial_active:
                return Response({'detail': 'You are not eligible for a trial.'}, status=status.HTTP_400_BAD_REQUEST)

            instance.is_on_trial = True
            instance.trial_start_date = timezone.now()
            instance.trial_ends_at = timezone.now() + timedelta(days=7)
            instance.save()

            return Response(UserSerializer(instance).data, status=status.HTTP_200_OK)

        # The 'me' action for update should use the appropriate serializer
        partial = kwargs.pop('partial', True) # For PATCH, partial should be True
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(UserSerializer(instance).data) # Return the full user data
    
    def perform_update(self, serializer):
        serializer.save()

class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        form = PasswordResetForm(request.data)
        if form.is_valid():
            email = form.cleaned_data['email']
            form.save(
                request=request,
                use_https=True,
                token_generator=default_token_generator,
                from_email=settings.DEFAULT_FROM_EMAIL,
                email_template_name='password_reset_email.html',
                extra_email_context={
                    'frontend_domain': settings.FRONTEND_DOMAIN,
                }
            )
            return Response({'detail': 'Password reset e-mail has been sent.'}, status=status.HTTP_200_OK)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uidb64 = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            serializer.save()
            return Response({'detail': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Invalid token or user ID.'}, status=status.HTTP_400_BAD_REQUEST)