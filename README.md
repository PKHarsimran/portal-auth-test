# Portal Auth Test

A small Flask-based authenticated portal for testing website downloaders and crawlers.

## Features

- Login page
- Protected dashboard, reports, and settings pages
- Redirect back to the requested page after login
- Logout route
- JS-style navigation via `data-url` and `onclick`
- Fake forgot/reset password pages
- Silent expired-session page that returns `200 OK`

## Default credentials

- Username: `admin`
- Password: `password123`

## Run with Docker Compose

```bash
docker compose up --build -d
