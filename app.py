from functools import wraps
import os

from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

PORTAL_USERNAME = os.getenv("PORTAL_USERNAME", "admin")
PORTAL_PASSWORD = os.getenv("PORTAL_PASSWORD", "password123")


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", redirectUrl=request.url))
        return view_func(*args, **kwargs)

    return wrapped_view


def render_portal(template_name, **context):
    return render_template(
        template_name,
        username=session.get("username", "user"),
        portal_sections=[
            {"label": "My Account", "endpoint": "my_account"},
            {"label": "Reports", "endpoint": "reports"},
            {"label": "Settings", "endpoint": "settings"},
        ],
        **context,
    )


@app.route("/")
def home():
    if session.get("logged_in"):
        return redirect(url_for("my_account"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    redirect_url = request.args.get("redirectUrl") or request.form.get(
        "redirect_url"
    ) or url_for("my_account")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == PORTAL_USERNAME and password == PORTAL_PASSWORD:
            session["logged_in"] = True
            session["username"] = username
            return redirect(redirect_url)

        error = "Invalid username or password."

    return render_template(
        "login.html",
        error=error,
        redirect_url=redirect_url,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


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
    ), 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
