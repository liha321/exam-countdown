# -*- coding: utf-8 -*-
"""
中考 / 高考 倒计时 · 桌面悬浮精美版
- 无边框 / 置顶 / 透明背景
- 圆角卡片 + 投影 + 高光 + 秒针脉冲 + 淡入动画
- 顶部胶囊（或 Tab 键）切换中考 / 高考
- 右键菜单打开「设置考试时间」，保存到同目录 config.json
- 鼠标左键拖动移动；右键菜单退出；ESC 退出
- 纯标准库，无需 pip 安装任何依赖
"""

import tkinter as tk
from tkinter import font as tkfont, messagebox
from datetime import datetime
import sys, os, json

# ==================== 默认配置（首次运行或无 config.json 时使用） ====================
DEFAULT_ZK = datetime(2027, 6, 20, 9, 0, 0)   # 中考开考时间
DEFAULT_GK = datetime(2030, 6, 7, 9, 0, 0)    # 高考开考时间
DEFAULT_EXAM = "zk"                            # 启动默认："zk" 中考 / "gk" 高考

# 窗口初始位置（距屏幕左 / 上像素）
INIT_X, INIT_Y = 200, 200

# 配色
COLOR_CARD      = "#1B1B2F"
COLOR_CARD_EDGE = "#33334F"
COLOR_SHADOW    = "#0A0A12"
COLOR_HILIGHT   = "#30304D"
COLOR_NUM       = "#FFFFFF"
COLOR_UNIT      = "#8E8EA8"
COLOR_DONE      = "#00E676"

# 两种考试强调色
ACCENT = {"zk": "#00E5FF", "gk": "#FFB74D"}

FONT_UI_PREFS  = ["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Micro Hei"]
FONT_NUM_PREFS = ["Consolas", "SF Mono", "Menlo", "DejaVu Sans Mono", "Courier New"]
SIZE_TITLE, SIZE_NUM, SIZE_UNIT, SIZE_TAB = 11, 30, 12, 10

TRANSPARENT_COLOR = "#010203"
CARD_W, CARD_H, CARD_GAP = 92, 86, 14
LEFT, TOP = 25, 68
WIN_W = LEFT * 2 + 4 * CARD_W + 3 * CARD_GAP
WIN_H = TOP + CARD_H + 10

# ==================== 配置文件（EXE 同目录 / 脚本同目录 config.json） ====================
def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(base_dir(), "config.json")
TIME_FMT = "%Y-%m-%d %H:%M"

def load_config():
    exams = {"zk": DEFAULT_ZK, "gk": DEFAULT_GK}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        for k in ("zk", "gk"):
            if raw.get(k):
                exams[k] = datetime.strptime(raw[k].strip(), TIME_FMT)
    except Exception:
        pass
    return exams

def save_config(exams):
    try:
        data = {k: exams[k].strftime(TIME_FMT) for k in ("zk", "gk")}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def pick_font(prefs):
    try:
        families = set(tkfont.families())
    except Exception:
        return "TkDefaultFont"
    for name in prefs:
        if name in families:
            return name
    return "TkDefaultFont"


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
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
        self.exams = load_config()
        self.exam_datetime = self.exams[self.current_exam]
        self.accent = ACCENT[self.current_exam]

        self.font_title = (pick_font(FONT_UI_PREFS), SIZE_TITLE, "bold")
        self.font_num   = (pick_font(FONT_NUM_PREFS), SIZE_NUM, "bold")
        self.font_unit  = (pick_font(FONT_UI_PREFS), SIZE_UNIT, "bold")
        self.font_tab  = (pick_font(FONT_UI_PREFS), SIZE_TAB, "bold")

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=TRANSPARENT_COLOR)
        try:
            self.root.attributes("-transparentcolor", TRANSPARENT_COLOR)
        except tk.TclError:
            self.root.attributes("-alpha", 0.95)
        self.root.geometry(f"{WIN_W}x{WIN_H}+{INIT_X}+{INIT_Y}")

        self.canvas = tk.Canvas(self.root, width=WIN_W, height=WIN_H,
                                bg=TRANSPARENT_COLOR, highlightthickness=0, bd=0)
        self.canvas.pack()

        self._build()
        self._bind_events()
        self._apply_exam()
        self._fade_in(0.0)
        self._tick()

    # ---------------- 界面构建 ----------------
    def _build(self):
        self.tab_items = {}
        for key, label, cx in (
            ("zk", "中考", WIN_W // 2 - 33),
            ("gk", "高考", WIN_W // 2 + 33),
        ):
            w, h = 58, 22
            x1, y1 = cx - w // 2, 16 - h // 2
            x2, y2 = cx + w // 2, 16 + h // 2
            rect = round_rect(self.canvas, x1, y1, x2, y2, 11,
                              fill=COLOR_CARD, outline=COLOR_CARD_EDGE, width=1)
            text = self.canvas.create_text(cx, 16, text=label, fill=COLOR_UNIT, font=self.font_tab)
            self.tab_items[key] = (rect, text)
            for item in (rect, text):
                self.canvas.tag_bind(item, "<ButtonRelease-1>",
                                     lambda e, k=key: self._on_tab_click(e, k))

        self.title_item = self.canvas.create_text(
            WIN_W // 2, 44, text="", fill=self.accent, font=self.font_title)

        units = ["天", "时", "分", "秒"]
        self.num_items = []
        for i, unit in enumerate(units):
            x1 = LEFT + i * (CARD_W + CARD_GAP)
            x2 = x1 + CARD_W
            y1, y2 = TOP, TOP + CARD_H
            cx = (x1 + x2) // 2
            round_rect(self.canvas, x1 + 3, y1 + 4, x2 + 3, y2 + 4, 16,
                       fill=COLOR_SHADOW, outline="")
            round_rect(self.canvas, x1, y1, x2, y2, 16,
                       fill=COLOR_CARD, outline=COLOR_CARD_EDGE, width=1)
            self.canvas.create_line(x1 + 16, y1 + 1, x2 - 16, y1 + 1,
                                    fill=COLOR_HILIGHT, width=2)
            it = self.canvas.create_text(cx, y1 + 30, text="00",
                                         fill=COLOR_NUM, font=self.font_num)
            self.num_items.append(it)
            self.canvas.create_text(cx, y1 + 66, text=unit,
                                    fill=COLOR_UNIT, font=self.font_unit)

    # ---------------- 事件绑定 ----------------
    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Button-1>", lambda e: self.root.focus_force(), add="+")
        self.canvas.bind("<Button-3>", self._on_right_menu)
        self.root.bind_all("<Escape>", lambda e: self.root.destroy())
        self.root.bind_all("<Tab>", self._on_tab_key)
        self.root.bind_all("<F2>", lambda e: self.open_settings())

    def _on_press(self, e):
        self._offset = (e.x, e.y)
        self._press_xy = (e.x, e.y)

    def _on_drag(self, e):
        nx = self.root.winfo_pointerx() - self._offset[0]
        ny = self.root.winfo_pointery() - self._offset[1]
        self.root.geometry(f"+{nx}+{ny}")

    def _on_right_menu(self, e):
        menu = tk.Menu(self.root, tearoff=0, bg=COLOR_CARD, fg=COLOR_NUM,
                       activebackground=ACCENT[self.current_exam], activeforeground="#0F0F1A")
        menu.add_command(label="设置考试时间 (F2)", command=self.open_settings)
        menu.add_separator()
        menu.add_command(label="退出", command=self.root.destroy)
        menu.tk_popup(e.x_root, e.y_root)

    def _on_tab_click(self, e, key):
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
        self.exam_datetime = self.exams[key]
        self.accent = ACCENT[key]
        self._done = False
        self._last_sec = -1
        self._apply_exam()
        self._render()

    def _apply_exam(self):
        key = self.current_exam
        accent = ACCENT[key]
        name = "中考" if key == "zk" else "高考"
        self.canvas.itemconfig(self.title_item,
                               text=f"距离 {self.exam_datetime.year} 年{name}还有",
                               fill=accent)
        for k, (rect, text) in self.tab_items.items():
            if k == key:
                self.canvas.itemconfig(rect, fill=accent, outline=accent)
                self.canvas.itemconfig(text, fill="#0F0F1A")
            else:
                self.canvas.itemconfig(rect, fill=COLOR_CARD, outline=COLOR_CARD_EDGE)
                self.canvas.itemconfig(text, fill=COLOR_UNIT)
        for it in self.num_items:
            self.canvas.itemconfig(it, fill=COLOR_NUM)

    # ---------------- 设置弹窗 ----------------
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("设置考试时间")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        try:
            win.grab_set()
        except tk.TclError:
            pass

        ui_font = (pick_font(FONT_UI_PREFS), 10)
        entries = {}
        row = 0
        for key, label in (("zk", "中考时间"), ("gk", "高考时间")):
            tk.Label(win, text=label, font=ui_font).grid(row=row, column=0, padx=12, pady=10, sticky="e")
            var = tk.StringVar(value=self.exams[key].strftime(TIME_FMT))
            ent = tk.Entry(win, textvariable=var, font=ui_font, width=18)
            ent.grid(row=row, column=1, padx=8, pady=10)
            entries[key] = var
            row += 1
        tk.Label(win, text="格式：年-月-日 时:分，例如 2027-06-20 09:00",
                 font=(pick_font(FONT_UI_PREFS), 8), fg=COLOR_UNIT
                 ).grid(row=row, column=0, columnspan=2, pady=(0, 6))

        def save():
            new = {}
            for k in ("zk", "gk"):
                try:
                    new[k] = datetime.strptime(entries[k].get().strip(), TIME_FMT)
                except ValueError:
                    messagebox.showerror("格式错误",
                                         f"{('中考' if k=='zk' else '高考')}时间格式不正确，\n请按 年-月-日 时:分 填写，例如 2027-06-20 09:00",
                                         parent=win)
                    return
            self.exams = new
            self.exam_datetime = new[self.current_exam]
            self._done = False
            self._last_sec = -1
            save_config(new)
            self._apply_exam()
            self._render()
            win.destroy()

        btns = tk.Frame(win)
        btns.grid(row=row + 1, column=0, columnspan=2, pady=8)
        tk.Button(btns, text="保存", font=ui_font, width=8, command=save).pack(side="left", padx=8)
        tk.Button(btns, text="取消", font=ui_font, width=8, command=win.destroy).pack(side="left", padx=8)

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
        if delta.total_seconds() <= 0:
            if not self._done:
                self._done = True
                for it in self.num_items:
                    self.canvas.itemconfig(it, text="0", fill=COLOR_DONE)
                self.canvas.itemconfig(self.title_item,
                                       text=f"{name}已开始 · 加油！", fill=COLOR_DONE)
            return
        d = delta.days
        h = delta.seconds // 3600
        m = (delta.seconds % 3600) // 60
        s = delta.seconds % 60
        self.canvas.itemconfig(self.num_items[0], text=str(d))
        self.canvas.itemconfig(self.num_items[1], text=f"{h:02d}")
        self.canvas.itemconfig(self.num_items[2], text=f"{m:02d}")
        self.canvas.itemconfig(self.num_items[3], text=f"{s:02d}")
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
