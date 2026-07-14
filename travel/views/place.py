from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from ..models import Project, Place
from ..serializers import PlaceSerializer, PlaceCreateSerializer, PlaceUpdateSerializer


class PlaceListCreateView(generics.ListCreateAPIView):
    serializer_class = PlaceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["visited"]

    def get_queryset(self):
        return Place.objects.filter(project_id=self.kwargs["project_id"])

    def create(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs["project_id"])

        if project.places.count() >= 10:
            return Response(
                {"detail": "A project can contain at most 10 places."},
                status=status.HTTP_409_CONFLICT,
            )

        create_serializer = PlaceCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        external_id = create_serializer.validated_data["external_id"]

        if project.places.filter(external_id=external_id).exists():
            return Response(
                {"detail": f"Place with external_id={external_id} is already in this project."},
                status=status.HTTP_409_CONFLICT,
            )

        artwork = create_serializer.context["artwork"]
        place = Place.objects.create(
            project=project,
            external_id=artwork["external_id"],
            title=artwork["title"],
            image_id=artwork["image_id"],
        )
        return Response(PlaceSerializer(place).data, status=status.HTTP_201_CREATED)


class PlaceDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PlaceSerializer

    def get_queryset(self):
        return Place.objects.filter(project_id=self.kwargs["project_id"])

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return PlaceUpdateSerializer
        return PlaceSerializer

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        place = self.get_object()

        project = place.project
        if not project.places.filter(visited=False).exists():
            project.status = Project.STATUS_COMPLETED
            project.save(update_fields=["status"])
        elif project.status == Project.STATUS_COMPLETED:
            project.status = Project.STATUS_ACTIVE
            project.save(update_fields=["status"])

        return Response(PlaceSerializer(place).data)
