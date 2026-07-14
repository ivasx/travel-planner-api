from django.db import models
from .project import Project


class Place(models.Model):
    project = models.ForeignKey(Project, related_name="places", on_delete=models.CASCADE)
    external_id = models.CharField(max_length=64)
    title = models.CharField(max_length=500, blank=True)
    image_id = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    visited = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "external_id"], name="unique_place_per_project")
        ]
