from functools import wraps
import io
import os
from datetime import timedelta
from urllib.parse import quote, unquote
import zipfile

from flask import (
    Flask,
    abort,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["SESSION_PERMANENT"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    seconds=int(os.getenv("REMEMBER_ME_DURATION_SECONDS", str(60 * 60 * 24 * 30)))
)

PORTAL_USERNAME = os.getenv("PORTAL_USERNAME", "admin")
PORTAL_PASSWORD = os.getenv("PORTAL_PASSWORD", "password123")
MAX_AUTH_REQUESTS = int(os.getenv("MAX_AUTH_REQUESTS", "8"))
ENABLE_FAKE_SSO = os.getenv("ENABLE_FAKE_SSO", "1") == "1"

USER_DIRECTORY = {
    "admin": {"password": PORTAL_PASSWORD, "role": "admin", "display_name": "Admin User"},
    "auditor": {"password": "password123", "role": "auditor", "display_name": "Audit Reviewer"},
    "member": {"password": "password123", "role": "member", "display_name": "Member Services"},
}

ROLE_LABELS = {
    "admin": "Administrator",
    "auditor": "Auditor",
    "member": "Member",
}

ROLE_ACCESS = {
    "admin": {"admin_tools", "audit_log", "member_services"},
    "auditor": {"audit_log"},
    "member": {"member_services"},
}

ROLE_PAGES = {
    "admin_tools": {
        "title": "Admin Tools",
        "description": "Privileged operational controls and identity-provider settings.",
        "summary": "Review fake SSO connections, session policies, and portal administration tasks.",
        "allowed_roles": ["admin"],
        "links": [
            ("Open Reports", "reports", {}),
            ("Download report bundle", "download_file", {"filename": "report-bundle.zip"}),
        ],
    },
    "audit_log": {
        "title": "Audit Log",
        "description": "Read-only access to authentication and export trail events.",
        "summary": "Inspect recent sign-in hops, exports, and downstream portal access patterns.",
        "allowed_roles": ["admin", "auditor"],
        "links": [
            ("Open Quarterly Review", "nested_section_detail", {"section": "reports", "slug": "quarterly-review"}),
            ("Download notice history", "download_file", {"filename": "notice-history.txt"}),
        ],
    },
    "member_services": {
        "title": "Member Services",
        "description": "Role-scoped service center content for standard members and support staff.",
        "summary": "View benefit documents, account support links, and service request resources.",
        "allowed_roles": ["admin", "member"],
        "links": [
            ("Benefits overview", "section_detail", {"slug": "benefits"}),
            ("Download handbook", "download_file", {"filename": "member-handbook.pdf"}),
        ],
    },
}

PORTAL_SECTIONS = [
    {"label": "My Account", "endpoint": "my_account"},
    {"label": "Reports", "endpoint": "reports"},
    {"label": "Settings", "endpoint": "settings"},
]

NESTED_SECTIONS = [
    {
        "label": "Policies",
        "items": [
            {"label": "Benefits", "endpoint": "section_detail", "slug": "benefits"},
            {"label": "Coverage", "endpoint": "section_detail", "slug": "coverage"},
        ],
    },
    {
        "label": "Library",
        "items": [
            {"label": "Downloads", "endpoint": "downloads"},
            {"label": "Quarterly Review", "endpoint": "nested_section_detail", "section": "reports", "slug": "quarterly-review"},
            {"label": "Delivery Preferences", "endpoint": "nested_section_detail", "section": "settings", "slug": "delivery-preferences"},
        ],
    },
]

SECTION_CONTENT = {
    "benefits": {
        "title": "Benefits Overview",
        "kicker": "Nested content",
        "description": "A deeper member section with protected links and download discovery targets.",
        "summary": "Review covered services, dependent setup, and renewal checkpoints.",
        "links": [
            ("Coverage details", "section_detail", {"slug": "coverage"}),
            ("Download handbook", "download_file", {"filename": "member-handbook.pdf"}),
        ],
    },
    "coverage": {
        "title": "Coverage Details",
        "kicker": "Nested content",
        "description": "Protected drill-down content for crawler path expansion.",
        "summary": "This section includes plan highlights, service classes, and downloadable schedules.",
        "links": [
            ("Benefits overview", "section_detail", {"slug": "benefits"}),
            ("Download coverage CSV", "download_file", {"filename": "coverage-schedule.csv"}),
        ],
    },
}

DEEP_SECTION_CONTENT = {
    ("reports", "quarterly-review"): {
        "title": "Quarterly Review",
        "kicker": "Reports / archive",
        "description": "Nested report archive page with links that look like a realistic portal document center.",
        "summary": "Open historical performance snapshots and bundled report exports.",
        "links": [
            ("Download report bundle", "download_file", {"filename": "report-bundle.zip"}),
            ("Go to reports", "reports", {}),
        ],
    },
    ("settings", "delivery-preferences"): {
        "title": "Delivery Preferences",
        "kicker": "Settings / notifications",
        "description": "Deep settings section for notification routing and stored delivery destinations.",
        "summary": "Manage secure inbox, email notices, and preferred export channels.",
        "links": [
            ("Download notice history", "download_file", {"filename": "notice-history.txt"}),
            ("Go to settings", "settings", {}),
        ],
    },
}

DOWNLOADS = {
    "member-handbook.pdf": (b"%PDF-1.4\n% Portal Auth Test member handbook\n", "application/pdf"),
    "coverage-schedule.csv": (
        b"tier,service,status\nGold,Primary Care,active\nSilver,Telehealth,active\n",
        "text/csv; charset=utf-8",
    ),
    "notice-history.txt": (
        b"2026-01-10,Email,Weekly digest\n2026-02-14,SMS,Security code\n",
        "text/plain; charset=utf-8",
    ),
}


def build_report_bundle():
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("summary.txt", "Quarterly portal report bundle\n")
        archive.writestr(
            "reports/utilization.csv",
            "month,utilization\n2026-01,78\n2026-02,81\n",
        )
    archive_buffer.seek(0)
    return archive_buffer.getvalue(), "application/zip"


DOWNLOADS["report-bundle.zip"] = build_report_bundle()


def current_role():
    return session.get("role", "member")


def build_role_navigation():
    role = current_role()
    allowed = ROLE_ACCESS.get(role, set())
    items = []
    for slug, page in ROLE_PAGES.items():
        if slug in allowed:
            items.append({"label": page["title"], "endpoint": "role_page", "slug": slug})
    return items


def build_js_menu_items():
    role = current_role()
    items = [
        {
            "label": "Quick Reports",
            "description": "Client-rendered link using data-route.",
            "url": url_for("reports"),
            "tone": "primary",
        },
        {
            "label": "Download Center",
            "description": "Client-rendered link using data-route.",
            "url": url_for("downloads"),
            "tone": "secondary",
        },
    ]
    if "audit_log" in ROLE_ACCESS.get(role, set()):
        items.append(
            {
                "label": "Audit Log",
                "description": f"Visible for {ROLE_LABELS[role].lower()} access.",
                "url": url_for("role_page", slug="audit_log"),
                "tone": "neutral",
            }
        )
    return items


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", redirectUrl=request.url))
        return view_func(*args, **kwargs)

    return wrapped_view


@app.before_request
def expire_session_after_request_limit():
    if request.endpoint in {
        "static",
        "login",
        "forgot_password",
        "reset_password",
        "health",
        "fake_sso_start",
        "fake_sso_callback",
        "fake_idp_authorize",
        "fake_idp_resume",
    }:
        return None

    if not session.get("logged_in"):
        return None

    requests_remaining = session.get("requests_remaining", MAX_AUTH_REQUESTS)
    requests_remaining -= 1
    session["requests_remaining"] = requests_remaining

    if requests_remaining < 0:
        session.clear()
        return redirect(url_for("login", expired=1, redirectUrl=request.url))

    return None



def render_portal(template_name, **context):
    role = current_role()
    return render_template(
        template_name,
        username=session.get("display_name") or session.get("username", "user"),
        account_name=session.get("username", "user"),
        current_role=role,
        role_label=ROLE_LABELS.get(role, role.title()),
        portal_sections=PORTAL_SECTIONS,
        nested_sections=NESTED_SECTIONS,
        role_navigation=build_role_navigation(),
        js_menu_items=build_js_menu_items(),
        fake_sso_enabled=ENABLE_FAKE_SSO,
        requests_remaining=session.get("requests_remaining", MAX_AUTH_REQUESTS),
        max_auth_requests=MAX_AUTH_REQUESTS,
        **context,
    )


@app.route("/")
def home():
    if session.get("logged_in"):
        return redirect(url_for("my_account"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = "Session expired. Please sign in again." if request.args.get("expired") else None
    redirect_url = request.args.get("redirectUrl") or request.form.get(
        "redirect_url"
    ) or url_for("my_account")
    use_sso = request.args.get("sso") == "1" or request.form.get("use_sso") == "1"

    if request.method == "POST":
        if use_sso and ENABLE_FAKE_SSO:
            return redirect(url_for("fake_sso_start", redirectUrl=redirect_url))

        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        remember_me = request.form.get("remember_me") == "on"
        user = USER_DIRECTORY.get(username)

        if user and password == user["password"]:
            session.clear()
            session["logged_in"] = True
            session["username"] = username
            session["display_name"] = user["display_name"]
            session["role"] = user["role"]
            session["requests_remaining"] = MAX_AUTH_REQUESTS
            session.permanent = remember_me
            return make_response(redirect(redirect_url))

        error = "Invalid username or password."

    return render_template(
        "login.html",
        error=error,
        redirect_url=redirect_url,
        fake_sso_enabled=ENABLE_FAKE_SSO,
        use_sso=use_sso,
        accounts=USER_DIRECTORY,
        role_labels=ROLE_LABELS,
    )


@app.route("/auth/sso/start")
def fake_sso_start():
    if not ENABLE_FAKE_SSO:
        return redirect(url_for("login"))

    redirect_url = request.args.get("redirectUrl") or url_for("my_account")
    relay_state = quote(redirect_url, safe="")
    return redirect(url_for("fake_idp_authorize", relay=relay_state))


@app.route("/auth/fake-idp/authorize")
def fake_idp_authorize():
    if not ENABLE_FAKE_SSO:
        return redirect(url_for("login"))

    relay_state = request.args.get("relay") or quote(url_for("my_account"), safe="")
    callback_url = url_for("fake_sso_callback", _external=False)
    return render_template(
        "fake_idp_authorize.html",
        relay_state=relay_state,
        callback_url=callback_url,
    )


@app.route("/auth/fake-idp/resume", methods=["POST"])
def fake_idp_resume():
    if not ENABLE_FAKE_SSO:
        return redirect(url_for("login"))

    relay_state = request.form.get("relay_state") or quote(url_for("my_account"), safe="")
    selected_user = request.form.get("sso_user", "admin").strip().lower()
    return redirect(url_for("fake_sso_callback", code=f"fake-code-{selected_user}", relay=relay_state))


@app.route("/auth/sso/callback")
def fake_sso_callback():
    if not ENABLE_FAKE_SSO:
        return redirect(url_for("login"))

    relay_state = request.args.get("relay") or quote(url_for("my_account"), safe="")
    selected_user = (request.args.get("code") or "fake-code-admin").replace("fake-code-", "")
    user = USER_DIRECTORY.get(selected_user, USER_DIRECTORY["admin"])

    session.clear()
    session["logged_in"] = True
    session["username"] = selected_user if selected_user in USER_DIRECTORY else "admin"
    session["display_name"] = user["display_name"]
    session["role"] = user["role"]
    session["requests_remaining"] = MAX_AUTH_REQUESTS
    session["sso_provider"] = "Fake Enterprise IDP"
    session["login_method"] = "fake-sso"
    return redirect(unquote(relay_state))


@app.route("/logout")
def logout():
    session.clear()
    response = make_response(redirect(url_for("login")))
    response.delete_cookie(app.config["SESSION_COOKIE_NAME"])
    return response


@app.route("/dashboard")
def dashboard_legacy():
    return redirect(url_for("my_account"))


@app.route("/reports")
def reports_legacy():
    return redirect(url_for("reports"))


@app.route("/settings")
def settings_legacy():
    return redirect(url_for("settings"))


@app.route("/site/my-account")
@login_required
def my_account():
    return render_portal("dashboard.html", active_section="my_account")


@app.route("/site/reports")
@login_required
def reports():
    return render_portal("reports.html", active_section="reports")


@app.route("/site/settings")
@login_required
def settings():
    return render_portal("settings.html", active_section="settings")


@app.route("/site/sections/<slug>")
@login_required
def section_detail(slug):
    section = SECTION_CONTENT.get(slug)
    if not section:
        return render_portal("403.html", active_section=None), 404
    return render_portal(
        "section_detail.html",
        active_section=None,
        section=section,
        breadcrumbs=[("My Account", url_for("my_account")), (section["title"], None)],
    )


@app.route("/site/<section>/<slug>")
@login_required
def nested_section_detail(section, slug):
    content = DEEP_SECTION_CONTENT.get((section, slug))
    if not content:
        return render_portal("403.html", active_section=None), 404
    parent_endpoint = section if section in {"reports", "settings"} else "my_account"
    return render_portal(
        "section_detail.html",
        active_section=parent_endpoint,
        section=content,
        breadcrumbs=[
            (parent_endpoint.replace("_", " ").title(), url_for(parent_endpoint)),
            (content["title"], None),
        ],
    )


@app.route("/site/role/<slug>")
@login_required
def role_page(slug):
    page = ROLE_PAGES.get(slug)
    if not page:
        abort(404)

    role = current_role()
    if slug not in ROLE_ACCESS.get(role, set()):
        return render_portal(
            "403.html",
            active_section=None,
            access_denied_title=page["title"],
            required_roles=[ROLE_LABELS[item] for item in page["allowed_roles"]],
        ), 403

    return render_portal(
        "role_page.html",
        active_section=None,
        page=page,
        breadcrumbs=[("Role Access", None), (page["title"], None)],
    )


@app.route("/site/downloads")
@login_required
def downloads():
    files = sorted(DOWNLOADS)
    return render_portal("downloads.html", active_section=None, files=files)


@app.route("/site/downloads/<path:filename>")
@login_required
def download_file(filename):
    file_info = DOWNLOADS.get(filename)
    if not file_info:
        return render_portal("403.html", active_section=None), 404

    file_bytes, mimetype = file_info
    return send_file(
        io.BytesIO(file_bytes),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


@app.route("/site/forbidden")
@login_required
def forbidden():
    return render_portal("403.html", active_section=None), 403


@app.route("/forgot-password")
def forgot_password():
    return render_template("forgot_password.html")


@app.route("/reset-password")
def reset_password():
    return render_template("reset_password.html")


@app.route("/silent-expired")
@app.route("/site/silent-expired")
def silent_expired():
    session.clear()
    return render_template(
        "login.html",
        error="Session expired. Please sign in again.",
        redirect_url=url_for("my_account"),
        fake_sso_enabled=ENABLE_FAKE_SSO,
        use_sso=False,
        accounts=USER_DIRECTORY,
        role_labels=ROLE_LABELS,
    ), 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
