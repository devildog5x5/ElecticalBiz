from datetime import datetime

from flask import jsonify, render_template

from api_spec import API_INDEX, OPENAPI_SPEC
from database import db, rows_to_list


def register_api_docs(app):
    @app.route("/api")
    def api_index():
        return jsonify(API_INDEX)

    @app.route("/api/health")
    def api_health():
        try:
            with db() as conn:
                conn.execute("SELECT 1").fetchone()
            db_status = "ok"
        except Exception as exc:
            db_status = f"error: {exc}"
        return jsonify({
            "status": "healthy" if db_status == "ok" else "degraded",
            "database": db_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0",
        })

    @app.route("/api/openapi.json")
    def openapi_json():
        return jsonify(OPENAPI_SPEC)

    @app.route("/api/docs")
    def api_docs_html():
        return render_template("api_docs.html")

    @app.route("/api/docs/markdown")
    def api_docs_markdown():
        from pathlib import Path
        md_path = Path(__file__).parent / "docs" / "API.md"
        if not md_path.exists():
            return jsonify({"error": "API.md not found"}), 404
        return app.response_class(md_path.read_text(encoding="utf-8"), mimetype="text/markdown")

    @app.route("/api/activity")
    def activity_log():
        from flask import request
        limit = min(int(request.args.get("limit", 50)), 200)
        entity_type = request.args.get("entity_type")
        with db() as conn:
            if entity_type:
                rows = conn.execute(
                    "SELECT * FROM activity_log WHERE entity_type = ? ORDER BY created_at DESC LIMIT ?",
                    (entity_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return jsonify(rows_to_list(rows))
