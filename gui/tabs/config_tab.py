import tkinter as tk
from tkinter import ttk


# API 环境配置
API_ENVIRONMENTS = {
    "正式环境": "",
    "测试环境": "http://api-test03.ucloudadmin.com",
}


class ConfigTab(ttk.Frame):
    """配置标签页：API URL、公私钥、项目ID"""

    def __init__(self, parent, state):
        super().__init__(parent, padding=16)
        self._state = state
        self._env_change_callbacks = []
        self._build()

    def add_env_change_callback(self, callback):
        """注册环境变化的回调函数，参数为当前环境名称"""
        self._env_change_callbacks.append(callback)

    def get_current_env(self):
        """返回当前选择的环境名称"""
        return self._env_var.get()

    def _build(self):
        self.columnconfigure(1, weight=1)

        # API 环境选择
        ttk.Label(self, text="API 环境").grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))

        self._env_var = tk.StringVar(value="正式环境")
        env_combo = ttk.Combobox(self, textvariable=self._env_var,
                                  values=list(API_ENVIRONMENTS.keys()),
                                  state="readonly", width=20)
        env_combo.grid(row=0, column=1, sticky="w", pady=4)
        env_combo.bind("<<ComboboxSelected>>", self._on_env_changed)

        # 其他字段
        fields = [
            ("Public Key", "public_key"),
            ("Private Key", "private_key"),
            ("项目 ID (多个用逗号分隔)", "project_ids"),
        ]
        self._vars = {}
        for idx, (label, attr) in enumerate(fields, start=1):
            ttk.Label(self, text=label).grid(row=idx, column=0, sticky="w", pady=4, padx=(0, 8))
            var = tk.StringVar()
            show = "*" if attr == "private_key" else ""
            entry = ttk.Entry(self, textvariable=var, show=show, width=60)
            entry.grid(row=idx, column=1, sticky="ew", pady=4)
            self._vars[attr] = var

    def _on_env_changed(self, event=None):
        """环境选择变化时的回调，通知所有注册的监听者"""
        env = self._env_var.get()
        for callback in self._env_change_callbacks:
            try:
                callback(env)
            except Exception:
                pass

    def get_values(self):
        env = self._env_var.get()
        self._state.api_url = API_ENVIRONMENTS.get(env, "")
        self._state.env_name = env

        for attr, var in self._vars.items():
            setattr(self._state, attr, var.get())

    def load_values(self):
        """从 state 恢复 UI 控件的值（用于配置记忆功能）"""
        # 根据 env_name 恢复环境选择，未知值回退到正式环境
        env_name = getattr(self._state, "env_name", "") or "正式环境"
        if env_name not in API_ENVIRONMENTS:
            env_name = "正式环境"
        self._env_var.set(env_name)

        # 触发回调（通知 resource_tab 切换 region 文件）
        self._on_env_changed()

        # 回填公私钥、项目ID（私钥不持久化，load 时一般为空字符串）
        for attr, var in self._vars.items():
            var.set(getattr(self._state, attr, ""))
