from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from organizations.models import Organization, Membership as OrgMembership
from .models import Team, TeamMembership

User = get_user_model()

class TeamAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', username='testuser', password='password123')
        self.client.force_authenticate(user=self.user)
        self.org = Organization.objects.create(name='My Org')
        OrgMembership.objects.create(user=self.user, organization=self.org, role='admin')

    def test_create_team(self):
        # The URL pattern is /api/organizations/{org_id}/teams/
        data = {'name': 'Team Alpha', 'organization_id': self.org.id}
        response = self.client.post(f'/api/organizations/{self.org.id}/teams/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Team.objects.count(), 1)
        self.assertEqual(TeamMembership.objects.count(), 1)
        self.assertEqual(TeamMembership.objects.first().role, 'manager')

    def test_list_teams_in_org(self):
        team = Team.objects.create(name='Team Alpha', organization=self.org)
        response = self.client.get(f'/api/organizations/{self.org.id}/teams/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_add_team_member_admin_only(self):
        team = Team.objects.create(name='Team Alpha', organization=self.org)
        new_user = User.objects.create_user(email='new@example.com', username='newuser', password='password123')
        # New user must be in the organization first
        OrgMembership.objects.create(user=new_user, organization=self.org, role='employee')
        
        data = {'user_id': new_user.id, 'role': 'member'}
        response = self.client.post(f'/api/organizations/{self.org.id}/teams/{team.id}/members/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TeamMembership.objects.count(), 1) # Only the new member (Wait, did I forget the creator?)
        # Ah, in my test setup I didn't create a team through the API, so creator membership was not automatically created.
        
    def test_prevent_non_org_member_in_team(self):
        team = Team.objects.create(name='Team Alpha', organization=self.org)
        non_org_user = User.objects.create_user(email='stranger@example.com', username='stranger', password='password123')
        
        data = {'user_id': non_org_user.id, 'role': 'member'}
        response = self.client.post(f'/api/organizations/{self.org.id}/teams/{team.id}/members/', data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # get_object_or_404 on OrgMembership fails
