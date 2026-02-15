from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountabilityPartnerViewSet

router = DefaultRouter()
router.register(r'partners', AccountabilityPartnerViewSet, basename='accountability-partner')

urlpatterns = [
    path('', include(router.urls)),
]