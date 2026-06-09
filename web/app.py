"""Flask 入口：路由 + SSE。"""
import os
from typing import Optional, Tuple

from flask import Flask, Response, jsonify, request, send_from_directory

from sdk.delete_all_resources import DELETE_OPERATIONS
from web.sse import stream_events
from web.task_manager import Task, TaskManager, _load_regions_for_env


def _err(code: str, http: int, message: Optional[str] = None) -> Tuple[Response, int]:
    return jsonify(error=message or code, code=code), http


def create_app(testing: bool = False) -> Tuple[Flask, TaskManager]:
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        static_url_path="",
    )
    manager = TaskManager(autostart=not testing)

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/regions")
    def get_regions():
        env = request.args.get("env", "prod")
        env_name = "测试环境" if env == "test" else "正式环境"
        try:
            return jsonify(_load_regions_for_env(env_name))
        except FileNotFoundError as e:
            return _err("INTERNAL", 500, str(e))

    @app.route("/api/resources")
    def get_resources():
        return jsonify([name for name, _ in DELETE_OPERATIONS])

    @app.route("/api/snapshot")
    def get_snapshot():
        return jsonify(manager.snapshot())

    # POST /api/tasks, /stop, GET /api/tasks/<id>, /stream
    # 实现在 Task 11/12 添加

    return app, manager
