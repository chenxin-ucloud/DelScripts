import threading
import logging
import sys
import os
import json
import queue
import time

from core.log_handler import QueueHandler
from core.state import AppState


def _resolve_sdk_path():
    """解析 SDK 路径，兼容 PyInstaller 打包环境"""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'sdk')
    # 开发环境: gui/core/runner.py → ../../sdk
    gui_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(os.path.dirname(gui_dir), 'sdk')


def run_deletion(state: AppState, log_queue: queue.Queue, stop_event: threading.Event,
                 on_done):
    """在后台线程中执行资源删除，完成后调用 on_done()"""

    try:
        sdk_path = _resolve_sdk_path()
        if sdk_path not in sys.path:
            sys.path.insert(0, sdk_path)

        try:
            import delete_all_resources as dar
        except ImportError as e:
            log_queue.put(f"[ERROR] 无法加载删除脚本: {e}")
            return

        # 为 SDK 的 logger 挂载 QueueHandler
        sdk_logger = logging.getLogger(dar.__name__)
        sdk_logger.handlers.clear()
        sdk_logger.setLevel(logging.INFO)
        handler = QueueHandler(log_queue)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        sdk_logger.addHandler(handler)

        assets_path = _resolve_assets_path()
        # 根据当前环境选择对应的区域配置文件
        region_filename = 'region_test.json' if state.env_name == '测试环境' else 'region.json'
        region_file = os.path.join(assets_path, region_filename)

        try:
            with open(region_file, 'r', encoding='utf-8') as f:
                all_regions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            log_queue.put(f"[ERROR] 无法加载区域配置文件 {region_filename}: {e}")
            return

        log_queue.put(f"[INFO] 当前环境: {state.env_name}, 加载区域文件: {region_filename}")

        # 筛选用户选择的区域
        regions = {k: v for k, v in all_regions.items() if k in state.selected_regions}

        # 筛选用户选择的资源操作
        selected_ops = [op for op in dar.DELETE_OPERATIONS if op[0] in state.selected_resources]

        # 解析项目ID列表
        project_ids = [p.strip() for p in state.project_ids.split(',') if p.strip()]
        if not project_ids:
            log_queue.put("[ERROR] 未配置项目ID")
            return

        log_queue.put("=" * 60)
        log_queue.put("开始批量删除资源")
        log_queue.put("=" * 60)

        # 确定 base_url
        base_url = state.api_url.strip() if state.api_url.strip() else None

        for loc_name, loc in regions.items():
            if stop_event.is_set():
                log_queue.put("[INFO] 用户已停止操作")
                break

            region = loc.get('Region')
            zone = loc.get('Zone')
            log_queue.put(f"\n处理区域: {loc_name} ({region})")

            for project_id in project_ids:
                if stop_event.is_set():
                    break

                client = dar.get_client(region, project_id, state.public_key, state.private_key, base_url)

                for resource_name, delete_func in selected_ops:
                    if stop_event.is_set():
                        break
                    try:
                        delete_func(client, loc_name, region, zone, project_id)
                    except Exception as e:
                        log_queue.put(f"[ERROR] [{loc_name}] 处理 {resource_name} 时发生错误: {e}")

        log_queue.put("\n" + "=" * 60)
        log_queue.put("批量删除资源完成")
        log_queue.put("=" * 60)
    finally:
        on_done()


def _resolve_assets_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'assets')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')
