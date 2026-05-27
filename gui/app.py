import tkinter as tk
from tkinter import ttk

from core.state import AppState
from core.config_store import load_config, save_config, apply_config_to_state
from tabs.config_tab import ConfigTab
from tabs.resource_tab import ResourceTab
from tabs.log_tab import LogTab


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UCloud Cleaner")
        self.geometry("900x680")
        self.resizable(True, True)
        self.minsize(720, 520)

        # 从磁盘加载上次配置，应用到 state
        self._state = AppState()
        saved = load_config()
        if saved:
            apply_config_to_state(self._state, saved)

        self._build()

        # 应用记忆的配置到 UI
        self._restore_ui_from_state()

        # 注册关闭窗口时保存配置
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self._config_tab = ConfigTab(notebook, self._state)
        self._resource_tab = ResourceTab(notebook, self._state)
        self._log_tab = LogTab(notebook, self._state, self._config_tab, self._resource_tab)

        notebook.add(self._config_tab, text="  配置  ")
        notebook.add(self._resource_tab, text="  资源选择  ")
        notebook.add(self._log_tab, text="  清理日志  ")

        # 环境变化时，资源选择 tab 自动加载对应区域文件
        def _on_env_changed(env_name):
            region_file = 'region_test.json' if env_name == '测试环境' else 'region.json'
            self._resource_tab.load_regions(region_file)

        self._config_tab.add_env_change_callback(_on_env_changed)

        # 监听标签页切换事件，自动设置焦点；同时根据当前环境同步区域文件
        def _on_tab_changed(event):
            selected_tab = event.widget.select()
            tab_index = event.widget.index(selected_tab)
            if tab_index == 1:  # 资源选择标签页
                # 切换到资源选择时，确保区域文件与当前环境一致
                env = self._config_tab.get_current_env()
                region_file = 'region_test.json' if env == '测试环境' else 'region.json'
                self._resource_tab.load_regions(region_file)
                # 延迟设置焦点，确保标签页已完全切换
                self.after(50, lambda: self._resource_tab.focus_region_canvas())

        notebook.bind("<<NotebookTabChanged>>", _on_tab_changed)

    def _restore_ui_from_state(self):
        """启动时把 state 中的记忆配置应用到 UI 控件"""
        # 1. 配置 tab：API 环境 + 公钥 + 项目ID（私钥不持久化，保持空）
        self._config_tab.load_values()
        # load_values 内部触发 _on_env_changed → 已经按环境加载对应 region 文件
        # 并在 load_regions 中按 state.selected_regions 恢复区域勾选

        # 2. 资源选择 tab：恢复资源类型勾选
        self._resource_tab.load_resource_selection()

    def _save_current_config(self):
        """把当前 UI 的值同步到 state 并保存到磁盘"""
        try:
            self._config_tab.get_values()
            self._resource_tab.get_values()
            save_config(self._state)
        except Exception:
            # 保存失败不应阻塞用户操作
            pass

    def _on_close(self):
        """关闭窗口前保存配置"""
        self._save_current_config()
        self.destroy()
