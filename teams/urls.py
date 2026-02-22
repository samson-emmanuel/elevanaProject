from rest_framework_nested import routers
from .views import TeamViewSet, TeamMembershipViewSet

# Main router for organizations
router = routers.SimpleRouter()
router.register(r'organizations/(?P<organization_pk>\d+)/teams', TeamViewSet, basename='organization-teams')

# Nested router for team memberships
teams_router = routers.NestedSimpleRouter(router, r'organizations/(?P<organization_pk>\d+)/teams', lookup='team')
teams_router.register(r'members', TeamMembershipViewSet, basename='team-memberships')

urlpatterns = [
    *router.urls,
    *teams_router.urls,
]
