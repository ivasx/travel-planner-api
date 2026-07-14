from rest_framework import generics, status
from rest_framework.response import Response

from ..models import Project
from ..serializers import ProjectSerializer, ProjectCreateSerializer, ProjectUpdateSerializer


class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.all().order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProjectCreateSerializer
        return ProjectSerializer


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ProjectUpdateSerializer
        return ProjectSerializer

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        instance = self.get_object()
        return Response(ProjectSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        if project.places.filter(visited=True).exists():
            return Response(
                {"detail": "Cannot delete a project that has visited places."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)
