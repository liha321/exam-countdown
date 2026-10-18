# -*- coding: utf-8 -*-
"""
中考 / 高考 倒计时 · 桌面悬浮精美版
- 无边框 / 置顶 / 透明背景
- 圆角卡片 + 投影 + 高光 + 秒针脉冲 + 淡入动画
- 顶部「中考 / 高考」胶囊切换（或按 Tab 键）
- 鼠标左键拖动移动；ESC 退出
- 纯标准库，无需 pip 安装任何依赖
"""

import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime

# ==================== 用户配置区 ====================

# 【中考开考时间】年, 月, 日, 时, 分, 秒
ZK_DATETIME = datetime(2027, 6, 20, 9, 0, 0)

# 【高考开考时间】年, 月, 日, 时, 分, 秒
GK_DATETIME = datetime(2030, 6, 7, 9, 0, 0)

# 启动时默认显示："zk" 中考 / "gk" 高考
DEFAULT_EXAM = "zk"

# 窗口初始位置（距屏幕左 / 上像素）
INIT_X, INIT_Y = 200, 200

# 配色
COLOR_CARD      = "#1B1B2F"   # 卡片底色
COLOR_CARD_EDGE = "#33334F"   # 卡片描边
COLOR_SHADOW    = "#0A0A12"   # 投影色
COLOR_HILIGHT   = "#30304D"   # 卡片顶部高光
COLOR_NUM       = "#FFFFFF"   # 数字颜色
COLOR_UNIT      = "#8E8EA8"   # 单位颜色
COLOR_DONE      = "#00E676"   # 考试已开始时的提示色

# 两种考试的强调色（标题 / 选中胶囊 / 秒针脉冲）
ACCENT = {
    "zk": "#00E5FF",   # 中考 · 青蓝
    "gk": "#FFB74D",   # 高考 · 金橙
}

# 字体候选列表（自动选系统里存在的第一个，跨平台不乱码）
FONT_UI_PREFS  = ["Microsoft YaHei", "PingFang SC",
                  "Noto Sans CJK SC", "WenQuanYi Micro Hei"]
FONT_NUM_PREFS = ["Consolas", "SF Mono", "Menlo",
                  "DejaVu Sans Mono", "Courier New"]

# 字号
SIZE_TITLE, SIZE_NUM, SIZE_UNIT, SIZE_TAB = 11, 30, 12, 10

# ====================================================

TRANSPARENT_COLOR = "#010203"   # 被系统当作"透明"的罕见色值

# 布局常量
CARD_W, CARD_H, CARD_GAP = 92, 86, 14
LEFT, TOP = 25, 68
WIN_W = LEFT * 2 + 4 * CARD_W + 3 * CARD_GAP   # 460
WIN_H = TOP + CARD_H + 10                       # 164


def pick_font(prefs):
    """从候选列表里选一个系统已安装的字体"""
    try:
        families = set(tkfont.families())
    except Exception:
        return "TkDefaultFont"
    for name in prefs:
        if name in families:
            return name
    return "TkDefaultFont"


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """平滑多边形绘制圆角矩形"""
    pts = [
        x1 + r, y1,  x2 - r, y1,  x2, y1,
        x2, y1 + r,  x2, y2 - r,  x2, y2,
        x2 - r, y2,  x1 + r, y2,  x1, y2,
        x1, y2 - r,  x1, y1 + r,  x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


class CountdownApp:
    def __init__(self, root):
        self.root = root
        self._done = False
        self._last_sec = -1
        self._offset = (0, 0)
        self._press_xy = (0, 0)
        self.current_exam = DEFAULT_EXAM
        self.exam_datetime = ZK_DATETIME if DEFAULT_EXAM == "zk" else GK_DATETIME
        self.accent = ACCENT[DEFAULT_EXAM]

        # 字体
        self.font_title = (pick_font(FONT_UI_PREFS),  SIZE_TITLE, "bold")
        self.font_num   = (pick_font(FONT_NUM_PREFS), SIZE_NUM,   "bold")
        self.font_unit  = (pick_font(FONT_UI_PREFS),  SIZE_UNIT,  "bold")
        self.font_tab   = (pick_font(FONT_UI_PREFS),  SIZE_TAB,   "bold")

        # ---------- 窗口属性 ----------
        self.root.overrideredirect(True)              # 无边框
        self.root.attributes("-topmost", True)        # 置顶
        self.root.configure(bg=TRANSPARENT_COLOR)
        try:
            self.root.attributes("-transparentcolor", TRANSPARENT_COLOR)
        except tk.TclError:
            self.root.attributes("-alpha", 0.95)      # Linux 降级
        self.root.geometry(f"{WIN_W}x{WIN_H}+{INIT_X}+{INIT_Y}")

        # ---------- 画布 ----------
        self.canvas = tk.Canvas(
            self.root, width=WIN_W, height=WIN_H,
            bg=TRANSPARENT_COLOR, highlightthickness=0, bd=0,
        )
        self.canvas.pack()

        self._build()
        self._bind_events()
        self._apply_exam()            # 初始化样式
        self._fade_in(0.0)            # 淡入
        self._tick()                  # 启动计时

    # ---------------- 界面构建 ----------------
    def _build(self):
        # ---- 顶部切换胶囊 ----
        self.tab_items = {}
        for key, label, cx in (
            ("zk", "中考", WIN_W // 2 - 33),
            ("gk", "高考", WIN_W // 2 + 33),
        ):
            w, h = 58, 22
            x1, y1 = cx - w // 2, 16 - h // 2
            x2, y2 = cx + w // 2, 16 + h // 2
            rect = round_rect(
                self.canvas, x1, y1, x2, y2, 11,
                fill=COLOR_CARD, outline=COLOR_CARD_EDGE, width=1,
            )
            text = self.canvas.create_text(
                cx, 16, text=label, fill=COLOR_UNIT, font=self.font_tab,
            )
            self.tab_items[key] = (rect, text)
            for item in (rect, text):
                self.canvas.tag_bind(
                    item, "<ButtonRelease-1>",
                    lambda e, k=key: self._on_tab_click(e, k),
                )

        # ---- 标题 ----
        self.title_item = self.canvas.create_text(
            WIN_W // 2, 44, text="", fill=self.accent, font=self.font_title,
        )

        # ---- 四张数字卡片 ----
        units = ["天", "时", "分", "秒"]
        self.num_items = []
        for i, unit in enumerate(units):
            x1 = LEFT + i * (CARD_W + CARD_GAP)
            x2 = x1 + CARD_W
            y1, y2 = TOP, TOP + CARD_H
            cx = (x1 + x2) // 2

            # 1) 投影
            round_rect(self.canvas, x1 + 3, y1 + 4, x2 + 3, y2 + 4,
                       16, fill=COLOR_SHADOW, outline="")
            # 2) 卡片主体
            round_rect(self.canvas, x1, y1, x2, y2,
                       16, fill=COLOR_CARD,
                       outline=COLOR_CARD_EDGE, width=1)
            # 3) 顶部高光
            self.canvas.create_line(
                x1 + 16, y1 + 1, x2 - 16, y1 + 1,
                fill=COLOR_HILIGHT, width=2,
            )
            # 4) 数字
            it = self.canvas.create_text(
                cx, y1 + 30, text="00",
                fill=COLOR_NUM, font=self.font_num,
            )
            self.num_items.append(it)
            # 5) 单位
            self.canvas.create_text(
                cx, y1 + 66, text=unit,
                fill=COLOR_UNIT, font=self.font_unit,
            )

    # ---------------- 事件绑定 ----------------
    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>",     self._on_drag)
        self.canvas.bind("<Button-1>",
                         lambda e: self.root.focus_force(), add="+")
        # ESC 退出
        self.root.bind_all("<Escape>", lambda e: self.root.destroy())
        # Tab 快速切换
        self.root.bind_all("<Tab>", self._on_tab_key)

    def _on_press(self, e):
        self._offset = (e.x, e.y)
        self._press_xy = (e.x, e.y)

    def _on_drag(self, e):
        nx = self.root.winfo_pointerx() - self._offset[0]
        ny = self.root.winfo_pointery() - self._offset[1]
        self.root.geometry(f"+{nx}+{ny}")

    def _on_tab_click(self, e, key):
        # 位移小于阈值才当作"点击"，避免拖动窗口时误触
        dx = abs(e.x - self._press_xy[0])
        dy = abs(e.y - self._press_xy[1])
        if dx + dy < 6:
            self.switch_to(key)

    def _on_tab_key(self, e):
        self._toggle()
        return "break"

    def _toggle(self):
        self.switch_to("gk" if self.current_exam == "zk" else "zk")

    # ---------------- 切换考试 ----------------
    def switch_to(self, key):
        if key == self.current_exam:
            return
        self.current_exam = key
        self.exam_datetime = ZK_DATETIME if key == "zk" else GK_DATETIME
        self.accent = ACCENT[key]
        self._done = False
        self._last_sec = -1        # 让下一次 _render 触发秒针脉冲
        self._apply_exam()
        self._render()             # 立即刷新，不等下一帧

    def _apply_exam(self):
        """把当前考试模式同步到界面样式"""
        key = self.current_exam
        accent = ACCENT[key]
        name = "中考" if key == "zk" else "高考"

        # 标题文字 + 强调色
        self.canvas.itemconfig(
            self.title_item,
            text=f"距离 {self.exam_datetime.year} 年{name}还有",
            fill=accent,
        )

        # 胶囊选中样式
        for k, (rect, text) in self.tab_items.items():
            if k == key:
                self.canvas.itemconfig(rect, fill=accent, outline=accent)
                self.canvas.itemconfig(text, fill="#0F0F1A")
            else:
                self.canvas.itemconfig(
                    rect, fill=COLOR_CARD, outline=COLOR_CARD_EDGE)
                self.canvas.itemconfig(text, fill=COLOR_UNIT)

        # 数字恢复正常白色（防止从"已开始"状态切回时仍是绿色）
        for it in self.num_items:
            self.canvas.itemconfig(it, fill=COLOR_NUM)

    # ---------------- 淡入动画 ----------------
    def _fade_in(self, v):
        try:
            self.root.attributes("-alpha", v)
        except tk.TclError:
            return
        if v < 0.99:
            self.root.after(18, lambda: self._fade_in(min(1.0, v + 0.08)))

    # ---------------- 倒计时刷新 ----------------
    def _tick(self):
        self._render()
        self.root.after(200, self._tick)

    def _render(self):
        delta = self.exam_datetime - datetime.now()
        name = "中考" if self.current_exam == "zk" else "高考"

        # 已到 / 已过考试时间
        if delta.total_seconds() <= 0:
            if not self._done:
                self._done = True
                for it in self.num_items:
                    self.canvas.itemconfig(it, text="0", fill=COLOR_DONE)
                self.canvas.itemconfig(
                    self.title_item,
                    text=f"{name}已开始 · 加油！",
                    fill=COLOR_DONE,
                )
            return

        d = delta.days
        h = delta.seconds // 3600
        m = (delta.seconds % 3600) // 60
        s = delta.seconds % 60

        self.canvas.itemconfig(self.num_items[0], text=str(d))
        self.canvas.itemconfig(self.num_items[1], text=f"{h:02d}")
        self.canvas.itemconfig(self.num_items[2], text=f"{m:02d}")
        self.canvas.itemconfig(self.num_items[3], text=f"{s:02d}")

        # 秒针脉冲
        if s != self._last_sec:
            self._last_sec = s
            self._pulse_seconds()

    def _pulse_seconds(self):
        it = self.num_items[3]
        self.canvas.itemconfig(it, fill=self.accent)
        self.root.after(160, lambda: self.canvas.itemconfig(it, fill=COLOR_NUM))


if __name__ == "__main__":
    root = tk.Tk()
    app = CountdownApp(root)
    root.focus_force()
    root.mainloop()