from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from travel.models import Place, Project
from .helpers import fetch_artwork_side_effect

PROJECTS_URL = "/api/projects/"


def project_url(pk):
    return f"/api/projects/{pk}/"


class ProjectAuthTests(APITestCase):
    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(PROJECTS_URL)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class ProjectCreateTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pw")
        self.client.force_authenticate(user=self.user)

    def test_create_project_without_places(self):
        response = self.client.post(PROJECTS_URL, {"name": "Weekend in Chicago"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Weekend in Chicago")
        self.assertEqual(response.data["places"], [])
        self.assertEqual(response.data["status"], "active")

    @patch("travel.serializers.project.fetch_artwork")
    def test_create_project_with_valid_places(self, mock_fetch):
        mock_fetch.side_effect = fetch_artwork_side_effect()

        payload = {
            "name": "Art Trip",
            "description": "Museums",
            "places": ["111", "222"],
        }
        response = self.client.post(PROJECTS_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["places"]), 2)
        self.assertEqual(Place.objects.count(), 2)
        self.assertEqual(mock_fetch.call_count, 2)

    @patch("travel.serializers.project.fetch_artwork")
    def test_create_project_rolls_back_when_a_place_is_invalid(self, mock_fetch):
        mock_fetch.side_effect = fetch_artwork_side_effect(missing_ids={"bad-id"})

        payload = {"name": "Broken Trip", "places": ["111", "bad-id"]}
        response = self.client.post(PROJECTS_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Project.objects.count(), 0)
        self.assertEqual(Place.objects.count(), 0)

    def test_create_project_rejects_more_than_ten_places(self):
        payload = {"name": "Too Many Places", "places": [str(i) for i in range(11)]}
        response = self.client.post(PROJECTS_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Project.objects.count(), 0)

    def test_create_project_rejects_duplicate_external_ids_in_same_request(self):
        payload = {"name": "Dup Places", "places": ["111", "111"]}
        response = self.client.post(PROJECTS_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Project.objects.count(), 0)

    def test_create_project_requires_name(self):
        response = self.client.post(PROJECTS_URL, {"description": "No name given"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProjectReadUpdateDeleteTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pw")
        self.client.force_authenticate(user=self.user)
        self.project = Project.objects.create(name="Rome Trip", description="Ancient sites")

    def test_list_projects(self):
        response = self.client.get(PROJECTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

    def test_filter_projects_by_status(self):
        Project.objects.create(name="Completed Trip", status=Project.STATUS_COMPLETED)

        response = self.client.get(PROJECTS_URL, {"status": "completed"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Completed Trip")

    def test_retrieve_single_project(self):
        response = self.client.get(project_url(self.project.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.project.id)

    def test_retrieve_missing_project_returns_404(self):
        response = self.client.get(project_url(999999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_project_fields(self):
        response = self.client.patch(
            project_url(self.project.id),
            {"name": "Rome Trip (updated)", "description": "New description"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Rome Trip (updated)")
        self.assertEqual(self.project.description, "New description")

    def test_update_cannot_change_status_directly(self):
        response = self.client.patch(
            project_url(self.project.id), {"status": "completed"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.STATUS_ACTIVE)

    def test_delete_project_without_visited_places(self):
        Place.objects.create(project=self.project, external_id="1", title="Colosseum")

        response = self.client.delete(project_url(self.project.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())

    def test_delete_project_with_visited_place_is_blocked(self):
        Place.objects.create(project=self.project, external_id="1", title="Colosseum", visited=True)

        response = self.client.delete(project_url(self.project.id))

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Project.objects.filter(id=self.project.id).exists())
