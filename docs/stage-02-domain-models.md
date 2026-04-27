# Stage 02: Domain Models

## Context

Work was completed on branch `dev`.

The goal of this stage was to add domain models without API logic and prepare the schema for the next booking-related steps.

## Added apps

- `apps.movies`
- `apps.halls`
- `apps.screenings`
- `apps.pricing`
- `apps.bookings`

All new apps were connected in `INSTALLED_APPS` via [core/settings.py](/home/erkin/Desktop/backend/core/settings.py).

## Added models

### Movies

- `Movie`
  - fields: `title`, `description`, `genre`, `duration`, `age_rating`, `poster_url`, `release_date`, `is_active`
  - choices: `MovieGenre`, `AgeRating`
  - constraints: `duration > 0`
  - indexes: title, activity + release date

### Halls

- `Hall`
  - fields: `name`, `rows`, `seats_per_row`, `schema_metadata`
  - constraints: `rows > 0`, `seats_per_row > 0`
  - indexes: capacity index, unique hall name

### Screenings

- `MovieSession`
  - fields: `movie`, `hall`, `start_datetime`, `end_datetime`, `is_active`
  - constraints: `end_datetime > start_datetime`, unique `(hall, start_datetime)`
  - indexes: by movie/start, hall/start, active/start

### Pricing

- `TicketPrice`
  - fields: `session`, `amount`, `currency`, `pricing_source`
  - choices: `TicketCurrency`, `PricingSource`
  - constraints: `amount > 0`, unique `(session, currency)`
  - indexes: `(session, currency)`, `pricing_source`

### Bookings

- `SeatHold`
  - fields: `session`, `user`, `seat_row`, `seat_number`, `expires_at`, `status`
  - choices: `SeatHoldStatus`
  - constraints:
    - `seat_row > 0`
    - `seat_number > 0`
    - unique active hold per seat in session
    - unique booked hold per seat in session
  - indexes: `(session, status)`, `(session, expires_at)`, `(user, status)`

- `Booking`
  - fields: `session`, `user`, `total_amount`, `booking_status`, `payment_status`, `confirmed_at`, `created_at`
  - choices: `BookingStatus`, `PaymentStatus`
  - constraints: `total_amount >= 0`
  - indexes: `(user, booking_status)`, `(session, booking_status)`, `(payment_status, created_at)`

- `BookingSeat`
  - fields: `booking`, `seat_row`, `seat_number`, `price_at_booking`
  - constraints:
    - `seat_row > 0`
    - `seat_number > 0`
    - `price_at_booking >= 0`
    - unique `(booking, seat_row, seat_number)`
  - indexes: `(seat_row, seat_number)`

## Migrations

Created initial migrations:

- `apps/movies/migrations/0001_initial.py`
- `apps/halls/migrations/0001_initial.py`
- `apps/screenings/migrations/0001_initial.py`
- `apps/pricing/migrations/0001_initial.py`
- `apps/bookings/migrations/0001_initial.py`

## Verification

The main project database remains PostgreSQL, but schema and tests for this stage were verified through temporary `sqlite` overrides to avoid dependency on a local PostgreSQL test database during development.

Verified:

- Django system check passes
- migrations are generated and in sync with models
- migrations apply successfully on a clean database
- `users + domain models` tests pass

## Commands executed

```bash
git branch --show-current
git status --short
rg --files
find apps -maxdepth 3 -type f | sort
DB_ENGINE=django.db.backends.sqlite3 SQLITE_DATABASE_NAME=/tmp/cinema-stage2-check.sqlite3 python manage.py check
DB_ENGINE=django.db.backends.sqlite3 SQLITE_DATABASE_NAME=/tmp/cinema-stage2-migrations.sqlite3 python manage.py makemigrations movies halls screenings pricing bookings
DB_ENGINE=django.db.backends.sqlite3 SQLITE_DATABASE_NAME=/tmp/cinema-stage2-verify.sqlite3 python manage.py migrate --noinput
DB_ENGINE=django.db.backends.sqlite3 SQLITE_DATABASE_NAME=/tmp/cinema-stage2-tests.sqlite3 python manage.py test apps.users apps.screenings apps.pricing apps.bookings
DB_ENGINE=django.db.backends.sqlite3 SQLITE_DATABASE_NAME=/tmp/cinema-stage2-check.sqlite3 python manage.py makemigrations --check --dry-run
```

## Next step

To apply this stage in the main development environment with PostgreSQL:

```bash
python manage.py migrate
```
