# Cinema Backend

Django REST backend for the cinema MVP. The project includes JWT auth, catalog endpoints for movies and sessions, admin setup for manual content management, and booking workflow with seat hold/confirm/cancel behavior.

## Stack

- Python 3.12
- Django 6
- Django REST Framework
- Simple JWT
- PostgreSQL

## Project Features

- `POST /api/v1/auth/register`, `login`, `refresh`, `logout`
- `GET /api/v1/movies/`, `GET /api/v1/movies/{id}/`
- `GET /api/v1/sessions/`, `GET /api/v1/sessions/{id}/`, `GET /api/v1/sessions/{id}/seats/`
- `POST /api/v1/bookings/`, `GET /api/v1/bookings/{id}/`, `POST /api/v1/bookings/{id}/confirm/`, `DELETE /api/v1/bookings/{id}/`
- Django admin for movies, halls, sessions, prices, bookings

## Environment

1. Copy `.env.example` to `.env`.
2. Adjust database and security values for your environment.
3. For Docker-based local setup, use `.env.docker.example` as the starting point instead.

Important runtime variables:

- `DB_*`: database connection settings
- `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, `JWT_REFRESH_TOKEN_LIFETIME_DAYS`
- `BOOKING_HOLD_MINUTES`: hold lifetime, default `10`
- `SEAT_POLLING_INTERVAL_SECONDS`: seat map polling hint, default `5`
- `DJANGO_BOOKINGS_LOG_LEVEL`: booking event logger level

## Local Run

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Apply migrations and run the server:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Admin will be available at `http://127.0.0.1:8000/admin/`.

## Docker Run

1. Start services with the docker-specific env file:

```bash
docker compose --env-file .env.docker.example up --build
```

2. If you need custom values, copy `.env.docker.example` to `.env.docker`, edit it, and run:

```bash
docker compose --env-file .env.docker up --build
```

The application will run on `http://127.0.0.1:8000/`. The container entrypoint applies migrations automatically before starting Django.

## Tests

Run the full application test suite on a temporary SQLite database:

```bash
DB_ENGINE=django.db.backends.sqlite3 SQLITE_DATABASE_NAME=/tmp/cinema-tests.sqlite3 python manage.py test apps.users apps.movies apps.screenings apps.pricing apps.bookings
```

## Logging

Booking lifecycle events are logged through the `bookings` logger:

- hold created
- hold conflict
- hold expired cleanup
- booking confirmed
- booking cancelled

All logs currently go to stdout, which keeps local runs and container logs simple.
