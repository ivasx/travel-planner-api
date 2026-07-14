from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from travel.models import Place, Project
from .helpers import fetch_artwork_side_effect


def places_url(project_id):
    return f"/api/projects/{project_id}/places/"


def place_url(project_id, place_id):
    return f"/api/projects/{project_id}/places/{place_id}/"


class PlaceCreateTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pw")
        self.client.force_authenticate(user=self.user)
        self.project = Project.objects.create(name="Chicago Trip")

    @patch("travel.serializers.place.fetch_artwork")
    def test_add_place_success(self, mock_fetch):
        mock_fetch.side_effect = fetch_artwork_side_effect()

        response = self.client.post(places_url(self.project.id), {"external_id": "27992"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["external_id"], "27992")
        self.assertEqual(response.data["visited"], False)
        self.assertEqual(Place.objects.filter(project=self.project).count(), 1)

    @patch("travel.serializers.place.fetch_artwork")
    def test_add_place_not_found_in_third_party_api_returns_400(self, mock_fetch):
        mock_fetch.side_effect = fetch_artwork_side_effect(missing_ids={"does-not-exist"})

        response = self.client.post(places_url(self.project.id), {"external_id": "does-not-exist"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Place.objects.count(), 0)

    @patch("travel.serializers.place.fetch_artwork")
    def test_add_duplicate_place_to_same_project_is_rejected(self, mock_fetch):
        mock_fetch.side_effect = fetch_artwork_side_effect()
        Place.objects.create(project=self.project, external_id="27992", title="Existing")

        response = self.client.post(places_url(self.project.id), {"external_id": "27992"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Place.objects.filter(project=self.project).count(), 1)

    @patch("travel.serializers.place.fetch_artwork")
    def test_same_external_id_allowed_in_different_projects(self, mock_fetch):
        mock_fetch.side_effect = fetch_artwork_side_effect()
        other_project = Project.objects.create(name="Other Trip")
        Place.objects.create(project=other_project, external_id="27992", title="Existing elsewhere")

        response = self.client.post(places_url(self.project.id), {"external_id": "27992"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("travel.serializers.place.fetch_artwork")
    def test_add_place_beyond_max_of_ten_is_rejected(self, mock_fetch):
        mock_fetch.side_effect = fetch_artwork_side_effect()
        for i in range(10):
            Place.objects.create(project=self.project, external_id=str(i), title=f"Place {i}")

        response = self.client.post(places_url(self.project.id), {"external_id": "extra"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Place.objects.filter(project=self.project).count(), 10)
        mock_fetch.assert_not_called()

    def test_add_place_to_missing_project_returns_404(self):
        response = self.client.post(places_url(999999), {"external_id": "1"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PlaceReadUpdateTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pw")
        self.client.force_authenticate(user=self.user)
        self.project = Project.objects.create(name="Chicago Trip")
        self.place_a = Place.objects.create(project=self.project, external_id="1", title="Place A")
        self.place_b = Place.objects.create(project=self.project, external_id="2", title="Place B")

    def test_list_places_for_project(self):
        response = self.client.get(places_url(self.project.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 2)

    def test_filter_places_by_visited(self):
        self.place_a.visited = True
        self.place_a.save(update_fields=["visited"])

        response = self.client.get(places_url(self.project.id), {"visited": "true"})

        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.place_a.id)

    def test_places_are_scoped_to_their_project(self):
        other_project = Project.objects.create(name="Other Trip")
        Place.objects.create(project=other_project, external_id="9", title="Not visible here")

        response = self.client.get(places_url(self.project.id))

        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 2)

    def test_retrieve_single_place(self):
        response = self.client.get(place_url(self.project.id, self.place_a.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.place_a.id)

    def test_retrieve_place_from_wrong_project_returns_404(self):
        other_project = Project.objects.create(name="Other Trip")
        response = self.client.get(place_url(other_project.id, self.place_a.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_notes(self):
        response = self.client.patch(
            place_url(self.project.id, self.place_a.id), {"notes": "Bring cash, no cards"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.place_a.refresh_from_db()
        self.assertEqual(self.place_a.notes, "Bring cash, no cards")

    def test_update_cannot_change_external_id_or_title(self):
        response = self.client.patch(
            place_url(self.project.id, self.place_a.id),
            {"external_id": "hacked", "title": "Hacked Title"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.place_a.refresh_from_db()
        self.assertEqual(self.place_a.external_id, "1")
        self.assertEqual(self.place_a.title, "Place A")


class ProjectCompletionBehaviorTests(APITestCase):
    """Marking all places visited should complete the project; unmarking should reopen it."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pw")
        self.client.force_authenticate(user=self.user)
        self.project = Project.objects.create(name="Chicago Trip")
        self.place_a = Place.objects.create(project=self.project, external_id="1", title="Place A")
        self.place_b = Place.objects.create(project=self.project, external_id="2", title="Place B")

    def test_project_completes_when_last_place_marked_visited(self):
        self.client.patch(place_url(self.project.id, self.place_a.id), {"visited": True}, format="json")
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.STATUS_ACTIVE)

        self.client.patch(place_url(self.project.id, self.place_b.id), {"visited": True}, format="json")
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.STATUS_COMPLETED)

    def test_project_reopens_when_a_visited_place_is_unmarked(self):
        self.place_a.visited = True
        self.place_a.save(update_fields=["visited"])
        self.place_b.visited = True
        self.place_b.save(update_fields=["visited"])
        self.project.status = Project.STATUS_COMPLETED
        self.project.save(update_fields=["status"])

        response = self.client.patch(
            place_url(self.project.id, self.place_a.id), {"visited": False}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.STATUS_ACTIVE)
