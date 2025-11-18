from django.utils import timezone
from django.db.models import Q
from django.http import Http404
from rest_framework import viewsets, permissions, decorators, response, status
from .models import Work, WorkStatus
from .serializers import WorkSerializer


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'is_admin', False))


class WorkViewSet(viewsets.ModelViewSet):
    queryset = Work.objects.select_related('owner').all()
    serializer_class = WorkSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['owner', 'status', 'is_public']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'is_admin', False):
            return qs
        # Owners see own items; others see published + permitted
        return qs.filter(Q(owner=user) | Q(status=WorkStatus.PUBLISHED, is_public=True))
    
    def get_object(self):
        """Override to provide specific 404 error message."""
        try:
            return super().get_object()
        except Http404:
            model_name = self.queryset.model._meta.verbose_name
            raise Http404(f"No {model_name} matches the given query.")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @decorators.action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def publish(self, request, pk=None):
        work = self.get_object()
        user = request.user
        if not (getattr(user, 'is_admin', False) or work.owner_id == user.id):
            return response.Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        work.status = WorkStatus.PUBLISHED
        work.published_at = timezone.now()
        work.save(update_fields=['status', 'published_at'])
        return response.Response(WorkSerializer(work).data)


