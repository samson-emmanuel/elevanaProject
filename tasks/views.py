from datetime import date
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import Task, TaskComment
from .serializers import TaskSerializer, TaskCommentSerializer


class TaskCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TaskComment.objects.filter(task_id=self.kwargs['task_pk']).select_related('author')

    def perform_create(self, serializer):
        task = Task.objects.get(pk=self.kwargs['task_pk'])
        user = self.request.user

        is_owner = task.owner == user
        is_org_member = task.organization and user.membership_set.filter(organization=task.organization).exists()
        is_accountability_partner = task.accountability_partnerships.filter(partner=user).exists()
        is_team_member = task.team and user.team_memberships.filter(team=task.team).exists()

        if not (is_owner or is_org_member or is_accountability_partner or is_team_member):
            raise PermissionDenied("You do not have permission to comment on this task.")

        serializer.save(author=user, task=task)

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("You can only delete your own comments.")
        instance.delete()


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related('owner', 'assignee').all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at']

    def get_queryset(self):
        user = self.request.user
        task_type = self.request.query_params.get('task_type')
        priority = self.request.query_params.get('priority')
        due_date = self.request.query_params.get('due_date')

        queryset = None

        if task_type == 'owned_by_me':
            # Tasks created by the user for themselves (or unassigned)
            queryset = Task.objects.filter(owner=user).filter(Q(assignee=user) | Q(assignee__isnull=True)).distinct()

        elif task_type == 'assigned_by_me':
            # Tasks created by the user and assigned to someone else
            queryset = Task.objects.filter(owner=user, assignee__isnull=False).exclude(assignee=user).distinct()

        elif task_type == 'assigned':
            # Tasks assigned to the user by others
            queryset = Task.objects.filter(assignee=user).exclude(owner=user).distinct()
        
        elif task_type == 'accountability':
            queryset = Task.objects.filter(accountability_partnerships__partner=user).distinct()

        elif task_type == 'team':
            user_teams = user.team_memberships.values_list('team_id', flat=True)
            queryset = Task.objects.filter(team_id__in=list(user_teams)).distinct()

        else:
            # Default to all tasks somehow related to the user (broadest query)
            org_ids = user.membership_set.values_list('organization_id', flat=True)
            user_teams = user.team_memberships.values_list('team_id', flat=True)
            queryset = Task.objects.filter(
                Q(owner=user) |
                Q(assignee=user) |
                Q(organization_id__in=list(org_ids)) |
                Q(team_id__in=list(user_teams)) |
                Q(accountability_partnerships__partner=user)
            ).distinct()

        if priority:
            queryset = queryset.filter(priority=priority)
        if due_date:
            queryset = queryset.filter(due_date__date=due_date)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        assignee = serializer.validated_data.get('assignee')
        organization = serializer.validated_data.get('organization')

        if assignee and assignee != user:
            # Assignment requires organization context and permissions
            if not organization:
                raise PermissionDenied("You cannot assign tasks outside of an organization.")

            try:
                creator_membership = Membership.objects.get(user=user, organization=organization)
                assignee_membership = Membership.objects.get(user=assignee, organization=organization)

                if creator_membership.role not in ['admin', 'manager']:
                    raise PermissionDenied("You must be an admin or manager to assign tasks.")
            
            except Membership.DoesNotExist:
                raise PermissionDenied("Both you and the assignee must be members of the organization.")

        serializer.save(owner=user)

    def perform_update(self, serializer):
        instance = self.get_object()
        user = self.request.user

        if instance.status == 'completed':
            raise PermissionDenied("Completed tasks cannot be updated.")

        can_update = False
        
        # 1. Personal task (no org), only owner can edit
        if not instance.organization and instance.owner == user:
            can_update = True
        
        # 2. Team-assigned task
        elif instance.team:
            is_org_admin = OrgMembership.objects.filter(
                user=user, 
                organization=instance.team.organization, 
                role='admin'
            ).exists()
            is_team_manager_or_assistant = TeamMembership.objects.filter(
                user=user,
                team=instance.team,
                role__in=['manager', 'assistant']
            ).exists()
            if is_org_admin or is_team_manager_or_assistant:
                can_update = True
                
        # 3. Org task not assigned to a team, only org admin can edit
        elif instance.organization:
             is_org_admin = OrgMembership.objects.filter(
                 user=user, 
                 organization=instance.organization, 
                 role='admin'
            ).exists()
             if is_org_admin:
                 can_update = True
        
        if not can_update:
            raise PermissionDenied("You do not have permission to edit this task.")
            
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if not instance.organization:
            # Personal task: only owner can delete
            if instance.owner != user:
                raise PermissionDenied("You do not have permission to delete this personal task.")
        else:
            # Organization task: only admin can delete
            is_admin = user.membership_set.filter(
                organization=instance.organization,
                role='admin'
            ).exists()
            if not is_admin:
                raise PermissionDenied("You must be an admin to delete this task.")

        if instance.status == 'completed':
            raise PermissionDenied("Completed tasks cannot be deleted.")
        instance.delete()

    @action(detail=False, methods=['get'], url_path='my-today')
    def my_today(self, request):
        tasks = self.get_queryset().filter(due_date__date=date.today(), status__in=['pending', 'in_progress'])
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)