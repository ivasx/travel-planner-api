from rest_framework import serializers
from ..models import Place
from ..services.artic_client import fetch_artwork


class PlaceSerializer(serializers.ModelSerializer):
    """Read-serializer for GET /places/ and GET /places/{id}/"""

    class Meta:
        model = Place
        fields = ["id", "external_id", "title", "image_id", "notes", "visited"]
        read_only_fields = ["id", "external_id", "title", "image_id"]


class PlaceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for PATCH /places/{id}/ — can change only notes and visited"""

    class Meta:
        model = Place
        fields = ["notes", "visited"]


class PlaceCreateSerializer(serializers.Serializer):
    """Serializer for POST /projects/{id}/places/ — accepts only external_id"""
    external_id = serializers.CharField(max_length=64)

    def validate_external_id(self, value):
        artwork = fetch_artwork(value)
        if artwork is None:
            raise serializers.ValidationError(
                f"Place with external_id={value} was not found in Art Institute API."
            )
        self.context["artwork"] = artwork
        return value
