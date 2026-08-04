from flask import jsonify, request

from reminders_service import (
    CATEGORY_LABELS,
    create_reminder,
    delete_reminder,
    get_email_settings,
    get_reminder,
    get_reminder_log,
    list_reminders,
    process_due_reminders,
    process_reminder,
    save_email_settings,
    send_email,
    update_reminder,
    wrap_html,
    get_email_settings as _settings,
)
from reminders_service import build_auto_content, parse_recipients


def register_reminder_routes(app):
    @app.route("/api/reminders/categories")
    def reminder_categories():
        return jsonify([{"id": k, "label": v} for k, v in CATEGORY_LABELS.items()])

    @app.route("/api/reminders/settings", methods=["GET", "PUT"])
    def reminder_settings():
        if request.method == "GET":
            s = get_email_settings()
            s["smtp_password"] = "********" if s.get("smtp_password") else ""
            return jsonify(s)
        return jsonify(save_email_settings(request.json))

    @app.route("/api/reminders/settings/test", methods=["POST"])
    def test_email():
        settings = get_email_settings()
        real = _settings()
        recipients = parse_recipients(real)
        if not recipients:
            return jsonify({"error": "Configure at least one recipient in To Emails"}), 400
        body = "This is a test email from PowerFlow. Your reminder notifications are configured correctly."
        result = send_email(
            "PowerFlow: Test email",
            wrap_html("Test Email", body),
            body,
            recipients,
            real,
        )
        if result.get("ok"):
            return jsonify({"ok": True, "message": f"Test email sent to {', '.join(recipients)}"})
        return jsonify({"error": result.get("error")}), 400

    @app.route("/api/reminders", methods=["GET", "POST"])
    def reminders_list():
        if request.method == "GET":
            items = list_reminders()
            for item in items:
                item["category_label"] = CATEGORY_LABELS.get(item["category"], item["category"])
            return jsonify(items)
        return jsonify(create_reminder(request.json)), 201

    @app.route("/api/reminders/<int:rid>", methods=["GET", "PUT", "DELETE"])
    def reminder_detail(rid):
        if request.method == "GET":
            r = get_reminder(rid)
            if not r:
                return jsonify({"error": "Not found"}), 404
            r["category_label"] = CATEGORY_LABELS.get(r["category"], r["category"])
            return jsonify(r)
        if request.method == "DELETE":
            delete_reminder(rid)
            return "", 204
        return jsonify(update_reminder(rid, request.json))

    @app.route("/api/reminders/<int:rid>/send", methods=["POST"])
    def send_reminder_now(rid):
        r = get_reminder(rid)
        if not r:
            return jsonify({"error": "Not found"}), 404
        settings = _settings()
        result = process_reminder(r, settings, force=True)
        if result.get("ok"):
            return jsonify(result)
        if result.get("skipped"):
            return jsonify(result)
        return jsonify({"error": result.get("error", "Send failed")}), 400

    @app.route("/api/reminders/run-due", methods=["POST"])
    def run_due_reminders():
        force = request.json.get("force_all", False) if request.json else False
        return jsonify(process_due_reminders(force_all=force))

    @app.route("/api/reminders/preview/<category>")
    def preview_reminder(category):
        subject, body = build_auto_content(category)
        if subject is None:
            return jsonify({"subject": None, "body": body, "empty": True})
        return jsonify({"subject": subject, "body": body, "empty": False})

    @app.route("/api/reminders/log")
    def reminder_log():
        limit = min(int(request.args.get("limit", 50)), 200)
        return jsonify(get_reminder_log(limit))
