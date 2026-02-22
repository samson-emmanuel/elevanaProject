from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.db import IntegrityError

from .models import Team, TeamMembership
from .serializers import TeamSerializer, TeamMembershipSerializer
from organizations.models import Organization, Membership as OrgMembership
from tasks.models import Task

class IsTeamAdminOrManager(IsAuthenticated):
    """
    Custom permission to only allow organization admins, organization managers,
    or team managers of a team to manage it.
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        user = request.user

        # For list/create actions, the permission is based on the organization.
        if view.action in ['list', 'create'] and 'organization_pk' in view.kwargs:
            org_pk = view.kwargs.get('organization_pk')
            try:
                membership = OrgMembership.objects.get(user=user, organization_id=org_pk)
                # Org Admins, Managers, and Employees can list teams.
                if view.action == 'list':
                    return membership.role in ['admin', 'manager', 'employee']
                # Only Org Admins and Managers can create teams.
                return membership.role in ['admin', 'manager']
            except OrgMembership.DoesNotExist:
                return False

        # For detail actions, we need to check permissions against the specific team.
        team_pk = view.kwargs.get('team_pk') or view.kwargs.get('pk')
        if not team_pk:
            return False # Cannot determine team context

        try:
            team = Team.objects.get(pk=team_pk)
        except Team.DoesNotExist:
            return False # Let the view handle the 404

        # Org Admin or Manager has full access
        is_org_admin_or_manager = OrgMembership.objects.filter(
            user=user,
            organization=team.organization,
            role__in=['admin', 'manager']
        ).exists()
        if is_org_admin_or_manager:
            return True

        # For read-only actions, any member of the organization can view.
        if view.action in ['retrieve', 'list']:
            is_org_member = OrgMembership.objects.filter(user=user, organization=team.organization).exists()
            if is_org_member:
                return True

        # Team Manager has full access to their team
        is_team_manager = TeamMembership.objects.filter(
            user=user,
            team=team,
            role='manager'
        ).exists()
        if is_team_manager:
            return True

        # Team Members have read-only access
        if view.action in ['retrieve', 'list']:
            is_team_member = TeamMembership.objects.filter(user=user, team=team).exists()
            return is_team_member

        return False


class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [IsTeamAdminOrManager]

    def get_queryset(self):
        user = self.request.user
        organization_pk = self.kwargs.get('organization_pk')

        if organization_pk:
            # Filter teams by organization if provided in URL (e.g., /organizations/{id}/teams/)
            # Only show teams within organizations the user is a member of.
            # get_object_or_404 is used here to ensure the user is part of the org
            get_object_or_404(OrgMembership, user=user, organization_id=organization_pk)
            return Team.objects.filter(organization_id=organization_pk).prefetch_related('memberships')
        else:
            # List all teams the user is a member of (across all organizations)
            return Team.objects.filter(memberships__user=user).distinct().prefetch_related('memberships') 


    def perform_create(self, serializer):
        organization_id = self.request.data.get('organization_id')
        if not organization_id:
            raise ValidationError({"organization_id": "Organization ID is required."})

        organization = get_object_or_404(Organization, pk=organization_id)

        # Permission check
        try:
            org_membership = OrgMembership.objects.get(user=self.request.user, organization=organization) 
            if org_membership.role not in ['admin', 'manager']:
                raise PermissionDenied("Only organization admins or managers can create teams.")
        except OrgMembership.DoesNotExist:
            raise PermissionDenied("You are not a member of this organization or do not have sufficient privileges.")

        try:
            team = serializer.save(created_by=self.request.user, organization=organization)
            # Automatically make the creator a manager of the team
            TeamMembership.objects.create(user=self.request.user, team=team, role='manager')
        except IntegrityError:
            raise ValidationError({"detail": "A team with this name already exists in this organization."})

    @action(detail=True, methods=['get'], url_path='reports')
    def team_reports(self, request, pk=None):
        team = self.get_object()
        team_members = team.memberships.all().values_list('user', flat=True)
        # Note: assuming 'members' was a many-to-many through membership
        # In our model, it's just 'memberships'

        team_tasks = Task.objects.filter(team=team)
        total_tasks = team_tasks.count()
        completed_tasks = team_tasks.filter(status='completed').count()
        pending_tasks = total_tasks - completed_tasks

        member_reports = []
        for member_id in team_members:
            member = User.objects.get(id=member_id)
            member_tasks = Task.objects.filter(assignee=member, team=team)
            member_total = member_tasks.count()
            member_completed = member_tasks.filter(status='completed').count()
            member_pending = member_total - member_completed
            member_reports.append({
                'id': member.id,
                'username': member.username,
                'total_tasks': member_total,
                'completed_tasks': member_completed,
                'pending_tasks': member_pending,
            })

        return Response({
            "team_id": team.id,
            "team_name": team.name,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "member_reports": member_reports,
        })

class TeamMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = TeamMembershipSerializer
    permission_classes = [IsTeamAdminOrManager]

    def get_queryset(self):
        team_pk = self.kwargs.get('team_pk')
        if not team_pk:
            return TeamMembership.objects.none()
        return TeamMembership.objects.filter(team_id=team_pk).select_related('user', 'team')

    def perform_create(self, serializer):
        team = get_object_or_404(Team, pk=self.kwargs['team_pk'])
        user_to_add = serializer.validated_data['user']

        # Check if max members limit (100) is reached
        if team.memberships.count() >= 100:
            raise ValidationError({"detail": "Maximum of 100 members per team reached."})

        # Permission check already handled by IsTeamAdminOrManager, but reinforce for clarity
        user = self.request.user
        can_add = False
        try:
            org_membership = OrgMembership.objects.get(user=user, organization=team.organization)
            if org_membership.role in ['admin', 'manager']:
                can_add = True
        except OrgMembership.DoesNotExist:
            pass

        if not can_add:
            try:
                team_membership = TeamMembership.objects.get(user=user, team=team)
                if team_membership.role == 'manager':
                    can_add = True
            except TeamMembership.DoesNotExist:
                pass

        if not can_add:
            raise PermissionDenied("You must be an organization admin/manager or team manager to add members.")

        try:
            # Additional check: ensure user to add is part of the organization
            get_object_or_404(OrgMembership, user=user_to_add, organization=team.organization)
            membership = serializer.save(team=team)
            return membership
        except IntegrityError:
            raise ValidationError({"detail": "User is already a member of this team."})
        except OrgMembership.DoesNotExist:
            raise ValidationError({"detail": "User is not a member of the organization this team belongs to."})

    def perform_update(self, serializer):
        team = get_object_or_404(Team, pk=self.kwargs['team_pk'])
        membership_to_update = self.get_object()

        # Permission check
        user = self.request.user
        can_update = False
        try:
            org_membership = OrgMembership.objects.get(user=user, organization=team.organization)
            if org_membership.role in ['admin', 'manager']:
                can_update = True
        except OrgMembership.DoesNotExist:
            pass

        if not can_update:
            try:
                team_manager_membership = TeamMembership.objects.get(user=user, team=team)
                if team_manager_membership.role == 'manager':
                    can_update = True
            except TeamMembership.DoesNotExist:
                pass

        if not can_update:
            raise PermissionDenied("You must be an organization admin/manager or team manager to update roles.")

        # Ensure the user changing role is not demoting themselves if they are the only manager
        if membership_to_update.role == 'manager' and serializer.validated_data.get('role') != 'manager': 
            other_managers_count = TeamMembership.objects.filter(team=team, role='manager').exclude(pk=membership_to_update.pk).count()
            if other_managers_count == 0:
                raise ValidationError({"detail": "A team must have at least one manager."})

        serializer.save()

    def perform_destroy(self, instance):
        team = instance.team
        user = self.request.user
        can_delete = False
        try:
            org_membership = OrgMembership.objects.get(user=user, organization=team.organization)
            if org_membership.role in ['admin', 'manager']:
                can_delete = True
        except OrgMembership.DoesNotExist:
            pass

        if not can_delete:
            try:
                team_manager_membership = TeamMembership.objects.get(user=user, team=team)
                if team_manager_membership.role == 'manager':
                    can_delete = True
            except TeamMembership.DoesNotExist:
                pass
        
        if not can_delete:
            raise PermissionDenied("You must be an organization admin/manager or team manager to remove members.")

        if instance.role == 'manager':
            other_managers_count = TeamMembership.objects.filter(team=instance.team, role='manager').exclude(pk=instance.pk).count()
            if other_managers_count == 0:
                raise ValidationError({"detail": "Cannot remove the last manager from a team."})
        instance.delete()
