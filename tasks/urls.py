from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, TaskCommentViewSet

router = DefaultRouter()
router.register(r'tasks', TaskViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('tasks/<int:task_pk>/comments/', TaskCommentViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('tasks/<int:task_pk>/comments/<int:pk>/', TaskCommentViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })),
]