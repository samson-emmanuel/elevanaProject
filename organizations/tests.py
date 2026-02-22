from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Organization, Membership

User = get_user_model()

class OrganizationAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', username='testuser', password='password123')
        self.client.force_authenticate(user=self.user)

    def test_create_organization(self):
        data = {'name': 'New Organization'}
        response = self.client.post('/api/organizations/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Membership.objects.count(), 1)
        self.assertEqual(Membership.objects.first().role, 'admin')

    def test_list_organizations(self):
        org = Organization.objects.create(name='My Org')
        Membership.objects.create(user=self.user, organization=org, role='employee')
        
        response = self.client.get('/api/organizations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'My Org')

    def test_update_organization_admin_only(self):
        org = Organization.objects.create(name='My Org')
        Membership.objects.create(user=self.user, organization=org, role='employee')
        
        data = {'name': 'Updated Name'}
        response = self.client.patch(f'/api/organizations/{org.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Change to admin
        membership = Membership.objects.get(user=self.user, organization=org)
        membership.role = 'admin'
        membership.save()
        
        response = self.client.patch(f'/api/organizations/{org.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        org.refresh_from_db()
        self.assertEqual(org.name, 'Updated Name')

    def test_invite_member(self):
        org = Organization.objects.create(name='My Org')
        Membership.objects.create(user=self.user, organization=org, role='admin')
        
        data = {
            'email': 'newmember@example.com',
            'role': 'employee',
            'first_name': 'New',
            'last_name': 'Member'
        }
        response = self.client.post(f'/api/organizations/{org.id}/invite-member/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(email='newmember@example.com').count(), 1)
        self.assertEqual(Membership.objects.filter(organization=org).count(), 2)
