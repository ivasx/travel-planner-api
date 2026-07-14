from rest_framework import serializers
from .place import PlaceSerializer
from ..models import Place, Project
from ..services.artic_client import fetch_artwork


class ProjectSerializer(serializers.ModelSerializer):
    """Read-serializer for listing project details, including nested places."""
    places = PlaceSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "description", "start_date", "status", "created_at", "places"]
        read_only_fields = ["id", "status", "created_at"]


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """Serializer for PUT/PATCH /projects/{id}/ — allows editing of name, description, and start_date."""

    class Meta:
        model = Project
        fields = ["name", "description", "start_date"]


class ProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for POST /projects/ — creation, optionally including a list of external_ids."""
    places = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Project
        fields = ["id", "name", "description", "start_date", "places"]
        read_only_fields = ["id"]

    def validate_places(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("A project can contain at most 10 places.")
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate external_id values in the request.")
        return value

    def create(self, validated_data):
        places_data = validated_data.pop("places", [])
        project = Project.objects.create(**validated_data)

        for external_id in places_data:
            artwork = fetch_artwork(external_id)
            if artwork is None:
                # Rollback project creation if an external_id is invalid
                project.delete()
                raise serializers.ValidationError(
                    f"Place with external_id={external_id} was not found in Art Institute API."
                )
            Place.objects.create(
                project=project,
                external_id=artwork["external_id"],
                title=artwork["title"],
                image_id=artwork["image_id"],
            )
        return project

    def to_representation(self, instance):
        # Return full ProjectSerializer structure after creation
        return ProjectSerializer(instance, context=self.context).data
