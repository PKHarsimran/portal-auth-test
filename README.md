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
- Fake SSO-like redirect chain that can be enabled or disabled
- JS-rendered sidebar menu items for client-side navigation discovery
- Role-based access pages for admin, auditor, and member personas

## Default credentials

- `admin` / `password123` — Administrator
- `auditor` / `password123` — Auditor
- `member` / `password123` — Member

Set `ENABLE_FAKE_SSO=0` to disable the optional fake SSO redirect chain.

## Run with Docker Compose

```bash
docker compose up --build -d
