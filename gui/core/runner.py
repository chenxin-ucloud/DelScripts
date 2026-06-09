import threading
import logging
import sys
import os
import json
import queue

from core.log_handler import QueueHandler
from core.state import AppState


def _resolve_sdk_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'sdk')
    gui_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(os.path.dirname(gui_dir), 'sdk')


def _resolve_assets_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'assets')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')


def run_deletion(state: AppState, log_queue: queue.Queue,
                 stop_event: threading.Event, on_done):
    """在后台线程中执行资源删除，完成后调用 on_done()"""
    try:
        sdk_path = _resolve_sdk_path()
        if sdk_path not in sys.path:
            sys.path.insert(0, sdk_path)
        # 把 sdk 的上层目录也加入，以便 `from sdk.runner_core import ...`
        sdk_parent = os.path.dirname(sdk_path)
        if sdk_parent not in sys.path:
            sys.path.insert(0, sdk_parent)

        try:
            import delete_all_resources as dar
            from sdk.runner_core import run_deletion_core
        except ImportError as e:
            log_queue.put(f"[ERROR] 无法加载删除脚本: {e}")
            return

        # 把 SDK 自己 logger 的输出转到队列（保留原有日志）
        sdk_logger = logging.getLogger(dar.__name__)
        sdk_logger.handlers.clear()
        sdk_logger.setLevel(logging.INFO)
        handler = QueueHandler(log_queue)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        sdk_logger.addHandler(handler)

        assets_path = _resolve_assets_path()
        region_filename = 'region_test.json' if state.env_name == '测试环境' else 'region.json'
        region_file = os.path.join(assets_path, region_filename)
        try:
            with open(region_file, 'r', encoding='utf-8') as f:
                all_regions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            log_queue.put(f"[ERROR] 无法加载区域配置文件 {region_filename}: {e}")
            return

        log_queue.put(f"[INFO] 当前环境: {state.env_name}, 加载区域文件: {region_filename}")
        project_ids = [p.strip() for p in state.project_ids.split(',') if p.strip()]
        if not project_ids:
            log_queue.put("[ERROR] 未配置项目ID")
            return

        # 适配 log_sink：runner_core 推 dict，这里转成字符串入 log_queue
        class _DictToStringSink:
            def put(self, item):
                if isinstance(item, dict):
                    log_queue.put(f"[{item.get('level','INFO')}] {item.get('line','')}")
                else:
                    log_queue.put(str(item))

        run_deletion_core(
            regions=all_regions,
            project_ids=project_ids,
            public_key=state.public_key,
            private_key=state.private_key,
            api_url=state.api_url,
            selected_regions=state.selected_regions,
            selected_resources=state.selected_resources,
            log_sink=_DictToStringSink(),
            stop_event=stop_event,
        )
    finally:
        on_done()
