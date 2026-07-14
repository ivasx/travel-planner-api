from django.urls import path
from .views import (
    ProjectListCreateView,
    ProjectDetailView,
    PlaceListCreateView,
    PlaceDetailView,
)

urlpatterns = [
    path("projects/", ProjectListCreateView.as_view()),
    path("projects/<int:pk>/", ProjectDetailView.as_view()),
    path("projects/<int:project_id>/places/", PlaceListCreateView.as_view()),
    path("projects/<int:project_id>/places/<int:pk>/", PlaceDetailView.as_view()),
]