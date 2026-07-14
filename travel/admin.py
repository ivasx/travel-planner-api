from django.contrib import admin
from .models import Project, Place


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "status", "start_date", "created_at"]
    list_filter = ["status"]


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ["id", "project", "external_id", "title", "visited"]
    list_filter = ["visited"]