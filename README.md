# Videoflix

![Python](https://img.shields.io/badge/python-3.12-blue)
![Django](https://img.shields.io/badge/django-4.2.27-092E20)
![DRF](https://img.shields.io/badge/DRF-3.16.1-red)

Videoflix is a Netflix-style video streaming backend built with **Django** and the **Django REST Framework**. It handles user registration with email activation, JWT-based login, password reset, and video metadata for a dashboard. It is designed to run fully containerized with **Docker**, **PostgreSQL** and **Redis**, and uses **Django RQ** for background jobs.

This project was built as the final backend project of the Developer Akademie training and follows a predefined [Definition of Done checklist](./documents/Videoflix%20Checkliste.pdf).

**GitHub Repository:**
[https://github.com/RichardWezel/Videoflix.git](https://github.com/RichardWezel/Videoflix.git)

**Frontend Repository:**
[https://github.com/RichardWezel/Videoflix_Frontend.git](https://github.com/RichardWezel/Videoflix_Frontend.git)

---

## Tech Stack

- Python 3.12
- Django 4.2.27
- Django REST Framework 3.16.1
- djangorestframework-simplejwt 5.5.1 (JWT auth via httpOnly cookies)
- PostgreSQL
- Redis + Django RQ (background tasks)
- Docker / docker-compose
- ffmpeg (installed in the image, prepared for HLS video processing)

All dependencies are listed in [`requirements.txt`](./requirements.txt).

---

## Getting Started

The project is designed to run entirely via Docker. Follow these steps to run the backend locally:

---

### 1. Clone the repository

```bash
git clone https://github.com/RichardWezel/Videoflix.git
cd Videoflix/Backend
```
---
### 2. Create the environment file

```bash
cp .env.template .env
```

Adjust the placeholder values (database credentials, email credentials, secret key, etc.) for your environment. See [Environment Variables](#environment-variables) below for details.

---
### 3. Build and start the containers

```bash
docker-compose up --build
```

-> if that doesn't work, use (without "-"):
```bash
docker compose up --build
```

This starts three containers: `web` (Django + Gunicorn + RQ worker), `db` (PostgreSQL) and `redis`. On startup, `backend.entrypoint.sh` automatically waits for the database, runs migrations, collects static files, creates a superuser from the environment variables, and starts the RQ worker.

---
### 4. Open the application

The API is available at [localhost:8000](http://localhost:8000).

The Django admin is available at [localhost:8000/admin](http://localhost:8000/admin), the RQ dashboard at [localhost:8000/django-rq](http://localhost:8000/django-rq).

---

## Project Structure

```plaintext
Videoflix/Backend/
│
├── core/                # Project settings and root urls.py
│
├── auth_app/            # Custom user model, registration, login, logout, password reset
│   └── api/
│       ├── views.py
│       ├── urls.py
│       ├── serializers.py
│       └── utils.py     # Email sending helpers
│
├── video_app/            # Video model and metadata endpoint
│   └── api/
│       ├── views.py
│       ├── urls.py
│       └── serializers.py
│
├── templates/             # HTML email templates (activation, password reset)
├── postman/                # Postman collection & environment for manual API testing
├── backend.Dockerfile
├── backend.entrypoint.sh
├── docker-compose.yml
└── requirements.txt
```

---

## Environment Variables

All required environment variables are stored in the [`.env`](./.env) file, based on [`.env.template`](./.env.template).

| Name | Description | Default |
| :--- | :---------- | :----- |
| `DJANGO_SUPERUSER_USERNAME` | Username for the auto-created Django admin superuser. | `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | Password for the auto-created superuser. | `adminpassword` |
| `DJANGO_SUPERUSER_EMAIL` | Email for the auto-created superuser (login is email-based). | `admin@example.com` |
| `SECRET_KEY` | Django cryptographic secret key. | — |
| `DEBUG` | Enables/disables debug mode. | `True` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames. | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated list of trusted origins for the frontend. | `http://localhost:5500,http://127.0.0.1:5500` |
| `DB_NAME` | PostgreSQL database name. | `your_database_name` |
| `DB_USER` | PostgreSQL user. | `your_database_user` |
| `DB_PASSWORD` | PostgreSQL password. | `your_database_password` |
| `DB_HOST` | PostgreSQL host (service name in Docker). | `db` |
| `DB_PORT` | PostgreSQL port. | `5432` |
| `REDIS_HOST` | Redis host (service name in Docker). | `redis` |
| `REDIS_LOCATION` | Redis cache location. | `redis://redis:6379/1` |
| `REDIS_PORT` | Redis port. | `6379` |
| `REDIS_DB` | Redis database index. | `0` |
| `EMAIL_HOST` | SMTP server for outgoing mail (activation/reset emails). | `smtp.example.com` |
| `EMAIL_PORT` | SMTP port. | `587` |
| `EMAIL_HOST_USER` | SMTP username. | `your_email_user` |
| `EMAIL_HOST_PASSWORD` | SMTP password. | `your_email_user_password` |
| `EMAIL_USE_TLS` | Enables TLS for email sending. | `True` |
| `EMAIL_USE_SSL` | Enables SSL for email sending. | `False` |
| `DEFAULT_FROM_EMAIL` | Sender address used by Django. | `EMAIL_HOST_USER` |

---

## Tests

Tests are written with Django's `APITestCase` and run with `pytest` / `coverage`.

```bash
docker-compose exec web coverage run manage.py test
docker-compose exec web coverage html
```

Current coverage:

- `auth_app`: registration (6 cases), activation (3 cases), login (4 cases), logout, token refresh.
- `video_app`: not yet covered.

---

## API Endpoints

### Authentication

<details>
    <summary>
        <span style="font-size: 16px; font-weight: bold;">
            POST `/api/register/`
        <span>
    </summary>
    <br>

Registers a new, inactive user account and sends an HTML activation email.

#### Request Body (JSON)
```json
{
  "email": "example@mail.de",
  "password": "examplePassword",
  "confirmed_password": "examplePassword"
}
```
#### Success Response (201 Created)
```json
{
  "user": {
    "id": 1,
    "email": "example@mail.de"
  },
  "token": "a1b2c3-activation-token"
}
```
#### Notes

- `password` and `confirmed_password` must match and pass Django's password validators.
- The email must be unique and valid.
- The created account is inactive until confirmed via `/api/activate/<uid>/<token>/`.

</details>
<hr>

<details>
    <summary>
        <span style="font-size: 16px; font-weight: bold;">
            GET `/api/activate/{uid}/{token}/`
        <span>
    </summary>
    <br>

Activates a user account via the link sent in the activation email.

#### URL Parameters

`uid`: `Base64-encoded user ID.`
`token`: `Token generated for account activation.`

#### Success Response (200 OK)
```json
{
  "message": "Account successfully activated!"
}
```
#### Notes

- Returns `400 Bad Request` if the link is invalid, expired, or the user doesn't exist.
- Returns `200 OK` with a notice if the account was already activated.

</details>
<hr>

<details>
    <summary>
        <span style="font-size: 16px; font-weight: bold;">
            POST `/api/login/`
        <span>
    </summary>
    <br>

Authenticates a user by email and password and returns JWT access/refresh tokens as httpOnly cookies.

#### Request Body (JSON)
```json
{
  "email": "example@mail.de",
  "password": "examplePassword"
}
```
#### Success Response (200 OK)
```json
{
  "detail": "Login successfully",
  "user": {
    "id": 1,
    "username": "example@mail.de"
  }
}
```
#### Notes

- Sets `access_token` and `refresh_token` as httpOnly cookies.
- Returns `401 Unauthorized` on invalid credentials or an inactive account.

</details>
<hr>

<details>
    <summary>
        <span style="font-size: 16px; font-weight: bold;">
            POST `/api/logout/`
        <span>
    </summary>
    <br>

Logs the user out by blacklisting the refresh token and clearing the auth cookies.

#### Success Response (200 OK)
```json
{
  "detail": "Logout successful! All tokens will be deleted. Refresh token is now invalid."
}
```
#### Notes

- Reads the refresh token from the `refresh_token` cookie.
- Deletes `access_token` and `refresh_token` cookies.

</details>
<hr>

<details>
    <summary>
        <span style="font-size: 16px; font-weight: bold;">
            POST `/api/token/refresh/`
        <span>
    </summary>
    <br>

Issues a new access token using the refresh token stored in the cookie.

#### Success Response (200 OK)
```json
{
  "detail": "Token refreshed",
  "access": "new-jwt-access-token"
}
```
#### Notes

- Reads the refresh token from the `refresh_token` cookie and sets a new `access_token` cookie.
- Returns `400 Bad Request` if no refresh token is present, `401 Unauthorized` if it's invalid.

</details>
<hr>

<details>
    <summary>
        <span style="font-size: 16px; font-weight: bold;">
            POST `/api/password_reset/`
        <span>
    </summary>
    <br>

Sends a password reset email to the given address, if an account exists for it.

#### Request Body (JSON)
```json
{
  "email": "example@mail.de"
}
```
#### Success Response (200 OK)
```json
{
  "detail": "An email has been sent to reset your password."
}
```
#### Notes

- Permissions required: none, publicly accessible.

</details>
<hr>

<details>
    <summary>
        <span style="font-size: 16px; font-weight: bold;">
            POST `/api/password_confirm/{uid}/{token}/`
        <span>
    </summary>
    <br>

Sets a new password for the user identified by `uid`, after validating the reset `token`.

#### URL Parameters

`uid`: `Base64-encoded user ID.`
`token`: `Token generated for password reset.`

#### Request Body (JSON)
```json
{
  "new_password": "newExamplePassword",
  "confirm_password": "newExamplePassword"
}
```
#### Success Response (200 OK)
```json
{
  "message": "Password has been reset successfully!"
}
```
#### Notes

- Returns `400 Bad Request` if the link is invalid/expired, or if the passwords don't match or don't pass validation.

</details>
<hr>

### Videos

<details>
    <summary>
        <span style="font-size: 16px; font-weight: bold;">
            GET `/api/video/`
        <span>
    </summary>
    <br>

Retrieves the metadata of all available videos, for the dashboard.

#### Headers

- Requires an authenticated request. Authenticated via the `access_token` httpOnly cookie set at login (`CookieJWTAuthentication`).

#### Success Response (200 OK)
```json
[
  {
    "id": 1,
    "created_at": "2026-07-30T12:00:00Z",
    "title": "Sample Video",
    "description": "A short description of the video.",
    "thumbnail_url": "https://example.com/thumbnail.jpg",
    "category": "Documentary"
  }
]
```
#### Notes

- Permissions required: the user must be authenticated.
- Videos are ordered by `created_at` (newest first), then by `title`.

</details>
<hr>

<details>
    <summary>
        <span style="font-size: 16px; font-weight: bold;">
            GET `/api/video/{movie_id}/{resolution}/index.m3u8` <em>(planned)</em>
        <span>
    </summary>
    <br>

Returns the HLS master playlist for a given movie and a chosen resolution.

#### Headers

- Requires an authenticated request (JWT via the `access_token` cookie, once implemented).

#### URL Parameters

| Name | Type | Description |
| :--- | :---: | :---------- |
| `movie_id` | int | The ID of the movie. |
| `resolution` | str | Desired resolution (e.g. `480p`, `720p`, `1080p`). |

#### Success Response (200 OK)

`Content-Type: application/vnd.apple.mpegurl`. Body contains the HLS manifest file in M3U8 format.

#### Status Codes

- `200`: Manifest successfully delivered.
- `404`: Video or manifest not found.

#### Rate Limits

- No limit.

#### Notes

- Permissions required: JWT authentication required.
- **Not yet implemented** — currently only documented per the API spec, no route/view exists yet in `video_app`.

</details>
<hr>

<details>
    <summary>
        <span style="font-size: 16px; font-weight: bold;">
            GET `/api/video/{movie_id}/{resolution}/{segment}/` <em>(planned)</em>
        <span>
    </summary>
    <br>

Returns a single HLS video segment for a given movie in the chosen resolution.

#### Headers

- Requires an authenticated request (JWT via the `access_token` cookie, once implemented).

#### URL Parameters

| Name | Type | Description |
| :--- | :---: | :---------- |
| `movie_id` | int | ID of the movie. |
| `resolution` | str | Desired resolution (e.g. `480p`, `720p`, `1080p`). |
| `segment` | str | File name of the segment (e.g. `000.ts`). |

#### Success Response (200 OK)

`Content-Type: video/MP2T`. Body contains binary video data.

#### Status Codes

- `200`: Segment successfully delivered.
- `404`: Video or segment not found.

#### Rate Limits

- No limit.

#### Notes

- Permissions required: JWT authentication required.
- **Not yet implemented** — currently only documented per the API spec, no route/view exists yet in `video_app`.

</details>
<hr>

---

## Project Status / Roadmap

Based on the project checklist (Definition of Done):

| Requirement | Status |
| :--- | :---: |
| Registration, login, logout, password reset | Done |
| Video dashboard (metadata endpoint) | Done |
| Docker / PostgreSQL / Redis / Django RQ setup | Done |
| Video streaming with multiple resolutions (480p/720p/1080p) via HLS | Not started |
| `video_app` test coverage | Not started |

---

---

## Docker

This project is fully containerized. See [Getting Started](#getting-started) for setup instructions.

## Frontend

A separate frontend application exists at [Videoflix_Frontend](https://github.com/RichardWezel/Videoflix_Frontend.git) and communicates with this backend via the REST API described above.
