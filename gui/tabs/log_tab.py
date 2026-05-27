import tkinter as tk
from tkinter import ttk, scrolledtext
import queue
import threading


class LogTab(ttk.Frame):
    """日志标签页：实时日志显示 + 开始/停止按钮"""

    POLL_INTERVAL = 100  # ms

    def __init__(self, parent, state, config_tab, resource_tab):
        super().__init__(parent, padding=16)
        self._state = state
        self._config_tab = config_tab
        self._resource_tab = resource_tab
        self._log_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker = None
        self._poll_id = None  # 保存 after() 返回的 ID，用于取消轮询
        self._build()

    def _build(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._text = scrolledtext.ScrolledText(
            self, state="disabled", wrap="word",
            font=("Menlo", 11), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white"
        )
        self._text.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=(0, 8))

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, columnspan=3, sticky="ew")

        self._start_btn = ttk.Button(btn_frame, text="开始清理", command=self._start)
        self._start_btn.pack(side="left", padx=(0, 8))

        self._stop_btn = ttk.Button(btn_frame, text="停止", command=self._stop, state="disabled")
        self._stop_btn.pack(side="left", padx=(0, 8))

        self._clear_btn = ttk.Button(btn_frame, text="清空日志", command=self._clear_log)
        self._clear_btn.pack(side="left")

        self._status_var = tk.StringVar(value="就绪")
        ttk.Label(btn_frame, textvariable=self._status_var).pack(side="right")

    def _append_log(self, text: str):
        self._text.configure(state="normal")
        self._text.insert("end", text + "\n")
        self._text.see("end")
        self._text.configure(state="disabled")

    def _clear_log(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")

    def _poll(self):
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        if self._worker and self._worker.is_alive():
            self._poll_id = self.after(self.POLL_INTERVAL, self._poll)
        else:
            self._poll_id = None

    def _start(self):
        # 收集最新配置
        self._config_tab.get_values()
        self._resource_tab.get_values()

        if not self._state.public_key or not self._state.private_key:
            self._append_log("[ERROR] 请先在「配置」标签页填写公私钥")
            return
        if not self._state.project_ids:
            self._append_log("[ERROR] 请先在「配置」标签页填写项目ID")
            return
        if not self._state.selected_regions:
            self._append_log("[ERROR] 请至少选择一个区域")
            return
        if not self._state.selected_resources:
            self._append_log("[ERROR] 请至少选择一种资源类型")
            return

        # 取消之前的轮询（如果存在）
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None

        # 持久化本次配置（不含私钥）以供下次启动自动恢复
        try:
            from core.config_store import save_config
            save_config(self._state)
        except Exception:
            pass

        self._stop_event.clear()
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._status_var.set("运行中...")

        from core.runner import run_deletion
        self._worker = threading.Thread(
            target=run_deletion,
            args=(self._state, self._log_queue, self._stop_event, self._on_done),
            daemon=True,
        )
        self._worker.start()
        self._poll_id = self.after(self.POLL_INTERVAL, self._poll)

    def _stop(self):
        self._stop_event.set()
        self._status_var.set("正在停止...")
        self._stop_btn.configure(state="disabled")

    def _on_done(self):
        # 由后台线程调用，通过 after 切回主线程
        self.after(0, self._finish)

    def _finish(self):
        # 排空队列
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._status_var.set("完成")
