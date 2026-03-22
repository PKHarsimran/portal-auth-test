# Portal Auth Test

A small Flask-based authenticated portal for testing website downloaders and crawlers.

## Features

- Login page
- Protected dashboard, reports, settings, and nested portal sections
- Redirect back to the requested page after login
- Logout route
- JS-style navigation via `data-url` and `onclick`
- Fake forgot/reset password pages
- Silent expired-session page that returns `200 OK`
- Session expiry after a configurable number of authenticated requests
- Remember-me login cookie for persistent sessions
- Protected file download endpoints

## Default credentials

- Username: `admin`
- Password: `password123`

## Run with Docker Compose

```bash
docker compose up --build -d
