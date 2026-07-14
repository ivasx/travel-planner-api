# Travel Planner API

A Django REST Framework application for managing travel projects and the places travelers want to visit within them.
Places are sourced and validated against the Art Institute of Chicago public API.

## Tech Stack

- Django 6.0
- Django REST Framework
- SQLite
- drf-spectacular (OpenAPI schema and Swagger UI)
- django-filter (query filtering)
- Art Institute of Chicago API (third-party place data and validation)

## Project Structure

config/ Django project configuration (settings, root URLs)
travel/
models/ Project and Place models
serializers/ Read/write serializers for both resources
services/ Third-party API client (Art Institute of Chicago)
views/ API views
admin.py Django admin registration
urls.py App-level URL routing

## Setup

### Requirements

- Python 3.12+
- pip

### Local installation

```bash
python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/api/`.

### Running with Docker

```bash
docker compose up --build
```

This runs migrations automatically on startup and starts the server on `http://127.0.0.1:8000/`. To create an admin/API
user inside the container:

```bash
docker compose exec web python manage.py createsuperuser
```

## Environment Variables

| Variable        | Default         | Description                                                        |
|-----------------|-----------------|--------------------------------------------------------------------|
| `SECRET_KEY`    | development key | Django secret key. Must be overridden in any non-local deployment. |
| `DEBUG`         | `True`          | Django debug mode.                                                 |
| `ALLOWED_HOSTS` | `*`             | Comma-separated list of allowed hosts.                             |

Copy `.env.example` to `.env` and adjust as needed if your setup reads environment files (docker-compose reads variables
from the shell environment or a local `.env` file automatically).

## Authentication

All API endpoints require HTTP Basic Authentication. Use the credentials of a Django user (created via `createsuperuser`
or through the admin panel).

Example with curl:

```bash
curl -u admin:yourpassword http://127.0.0.1:8000/api/projects/
```

In Postman, set the Authorization tab to Basic Auth and provide the same credentials. The Swagger UI and OpenAPI schema
endpoints are exempt from authentication so the API documentation remains publicly browsable.

## API Documentation

- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- Raw OpenAPI schema: `http://127.0.0.1:8000/api/schema/`
- Django admin: `http://127.0.0.1:8000/admin/`

## Endpoints

### Projects

| Method    | Path                  | Description                                                                                |
|-----------|-----------------------|--------------------------------------------------------------------------------------------|
| POST      | `/api/projects/`      | Create a project, optionally with an initial list of places (`places: [external_id, ...]`) |
| GET       | `/api/projects/`      | List projects. Supports `?status=active` or `?status=completed` and pagination (`?page=`)  |
| GET       | `/api/projects/{id}/` | Retrieve a single project with its places                                                  |
| PUT/PATCH | `/api/projects/{id}/` | Update name, description, or start date                                                    |
| DELETE    | `/api/projects/{id}/` | Delete a project. Returns 409 if any place has been marked visited                         |

### Places

| Method    | Path                                    | Description                                                                                                       |
|-----------|-----------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| POST      | `/api/projects/{id}/places/`            | Add a place to a project by `external_id`. Validated against the Art Institute of Chicago API before being stored |
| GET       | `/api/projects/{id}/places/`            | List places in a project. Supports `?visited=true` or `?visited=false` and pagination                             |
| GET       | `/api/projects/{id}/places/{place_id}/` | Retrieve a single place                                                                                           |
| PUT/PATCH | `/api/projects/{id}/places/{place_id}/` | Update `notes` and/or `visited`                                                                                   |

## Example Requests

Create a project with places:

```bash
curl -u admin:yourpassword -X POST http://127.0.0.1:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Chicago Trip", "description": "Art museums", "places": ["27992"]}'
```

Mark a place as visited:

```bash
curl -u admin:yourpassword -X PATCH http://127.0.0.1:8000/api/projects/1/places/1/ \
  -H "Content-Type: application/json" \
  -d '{"visited": true}'
```

## Business Rules

- A project can hold at most 10 places.
- The same `external_id` cannot be added to the same project more than once.
- A place must exist in the Art Institute of Chicago API before it is stored.
- A project cannot be deleted while any of its places are marked as visited.
- A project's status automatically switches to `completed` once every place in it is marked as visited, and reverts to
  `active` if a place is later unmarked.

## Design Notes

- The `places` field on project creation is optional. This allows a project to be created first and populated
  incrementally through the "add place" endpoint, rather than forcing all places to be known upfront. Places already in
  a project are still capped at 10 and validated against duplicates and the third-party API regardless of how they are
  added.
- Place metadata (`title`, `image_id`) is copied from the Art Institute of Chicago API response at creation time and
  cached for one hour, so repeated lookups of the same artwork do not require a new external request.
- Basic Authentication is applied globally across the API. This was chosen over a mixed public/private split for
  simplicity and to clearly demonstrate the authentication requirement; Swagger and schema endpoints remain open so the
  API can be inspected without credentials.

## Caching

Responses from the Art Institute of Chicago API are cached in-memory (Django's local memory cache) for one hour per
`external_id`, reducing redundant calls to the third-party service during validation and project creation.