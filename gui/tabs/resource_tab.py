import sys
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox


def _get_assets_dir():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'assets')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')


def _load_regions(filename='region.json'):
    assets = _get_assets_dir()
    with open(os.path.join(assets, filename), 'r', encoding='utf-8') as f:
        return list(json.load(f).keys())


ALL_RESOURCES = [
    "UHost", "UDisk", "NATGW", "UNI", "ALB", "NLB",
    "EIP", "UGN", "UWAN", "SecurityGroup", "ACL", "Subnet", "VPC",
]


class ResourceTab(ttk.Frame):
    """资源选择标签页：区域 + 资源类型复选框"""

    def __init__(self, parent, state):
        super().__init__(parent, padding=16)
        self._state = state
        self._region_vars = {}
        self._resource_vars = {}
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # ---- 区域选择 ----
        region_frame = ttk.LabelFrame(self, text="区域", padding=8)
        region_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))

        btn_frame = ttk.Frame(region_frame)
        btn_frame.pack(fill="x", pady=(0, 4))
        ttk.Button(btn_frame, text="全选", command=self._select_all_regions).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="取消选择", command=self._deselect_all_regions).pack(side="left", padx=2)

        canvas = tk.Canvas(region_frame, height=320, highlightthickness=0)
        scrollbar = ttk.Scrollbar(region_frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _content_overflows():
            """检查内容是否超过 Canvas 可视区域"""
            bbox = canvas.bbox("all")
            if not bbox:
                return False
            content_height = bbox[3] - bbox[1]
            visible_height = canvas.winfo_height()
            return content_height > visible_height

        def _on_inner_configure(_event):  # noqa: tkinter 回调必须有 event 参数
            """内容变化时更新 scrollregion，并根据需要显隐滚动条"""
            del _event
            canvas.configure(scrollregion=canvas.bbox("all"))
            if _content_overflows():
                scrollbar.pack(side="right", fill="y")
            else:
                scrollbar.pack_forget()
                # 内容不溢出时复位到顶部
                canvas.yview_moveto(0)

        inner.bind("<Configure>", _on_inner_configure)

        # 绑定鼠标滚轮事件（兼容 macOS 和 Windows/Linux）
        def _on_mousewheel(event):
            if not _content_overflows():
                return
            # macOS 使用 event.delta 直接表示滚动量
            canvas.yview_scroll(int(-1 * (event.delta)), "units")

        def _on_mousewheel_linux(event):
            if not _content_overflows():
                return
            # Linux 使用 Button-4 和 Button-5
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        # macOS 和 Windows
        canvas.bind("<MouseWheel>", _on_mousewheel)
        # Linux
        canvas.bind("<Button-4>", _on_mousewheel_linux)
        canvas.bind("<Button-5>", _on_mousewheel_linux)

        # 鼠标进入时自动获得焦点，使滚轮立即生效
        canvas.bind("<Enter>", lambda e: canvas.focus_set())

        canvas.pack(side="left", fill="both", expand=True)
        # 滚动条由 _on_inner_configure 根据内容是否溢出动态显隐

        # 保存 canvas 引用供后续使用
        self._region_canvas = canvas
        self._region_inner = inner
        self._current_region_file = None

        # 初始加载默认区域（正式环境）
        self.load_regions('region.json')

        # ---- 资源类型选择 ----
        res_frame = ttk.LabelFrame(self, text="资源类型", padding=8)
        res_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))

        btn_frame2 = ttk.Frame(res_frame)
        btn_frame2.pack(fill="x", pady=(0, 4))
        ttk.Button(btn_frame2, text="全选", command=self._select_all_resources).pack(side="left", padx=2)
        ttk.Button(btn_frame2, text="取消选择", command=self._deselect_all_resources).pack(side="left", padx=2)

        for res in ALL_RESOURCES:
            var = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(res_frame, text=res, variable=var)
            cb.pack(anchor="w")
            self._resource_vars[res] = var

    def load_regions(self, filename='region.json'):
        """根据指定的区域配置文件重新加载区域复选框"""
        if self._current_region_file == filename:
            return  # 已加载，不重复处理

        # 清空现有区域复选框
        for widget in self._region_inner.winfo_children():
            widget.destroy()
        self._region_vars.clear()

        try:
            regions = _load_regions(filename)
        except Exception as e:
            messagebox.showerror(
                "加载区域配置失败",
                f"无法加载 {filename} 文件:\n{e}\n\n请检查文件是否存在且格式正确。"
            )
            self._current_region_file = filename
            return

        # 如果 state 中保存了上次的选中区域，按其恢复；否则默认全选
        remembered = set(getattr(self._state, "selected_regions", None) or [])
        # 仅当 remembered 与当前 region 文件有交集时才使用记忆，否则全选
        use_remembered = bool(remembered.intersection(regions))

        for region in regions:
            default = (region in remembered) if use_remembered else True
            var = tk.BooleanVar(value=default)
            cb = ttk.Checkbutton(self._region_inner, text=region, variable=var)
            cb.pack(anchor="w")
            self._region_vars[region] = var

        self._current_region_file = filename
        # 滚动条复位到顶部
        self._region_canvas.yview_moveto(0)

    def load_resource_selection(self):
        """根据 state.selected_resources 恢复资源类型勾选状态"""
        remembered = set(getattr(self._state, "selected_resources", None) or [])
        if not remembered:
            return  # 未保存过，保持默认（全选）
        for res, var in self._resource_vars.items():
            var.set(res in remembered)

    def _select_all_regions(self):
        for v in self._region_vars.values():
            v.set(True)

    def _deselect_all_regions(self):
        for v in self._region_vars.values():
            v.set(False)

    def _select_all_resources(self):
        for v in self._resource_vars.values():
            v.set(True)

    def _deselect_all_resources(self):
        for v in self._resource_vars.values():
            v.set(False)

    def get_values(self):
        self._state.selected_regions = [r for r, v in self._region_vars.items() if v.get()]
        self._state.selected_resources = [r for r, v in self._resource_vars.items() if v.get()]

    def focus_region_canvas(self):
        """设置区域 Canvas 的焦点，使滚轮立即生效"""
        if hasattr(self, '_region_canvas'):
            self._region_canvas.focus_set()
