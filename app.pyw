"""🧹 סדרן ההורדות: חלון עם כפתור שמפעיל את הסוכן, ופס התקדמות חי."""
import os

# לא שולחים קבצים אישיים ל-LangSmith בשימוש היומיומי (רק בזמן פיתוח)
os.environ["LANGSMITH_TRACING"] = "false"

import queue
import threading
import time
import uuid
import tkinter as tk
from tkinter import ttk

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

import config
from graph import build_graph

graph = build_graph(checkpointer=InMemorySaver())

# ===== עיצוב: מצב כהה עם סגול-ורוד =====
BG = "#0F0E17"
CARD = "#1A1826"
BORDER = "#2C2945"
TEXT = "#ECEAF6"
MUTED = "#8A86A3"
START = "#8B5CF6"       # סגול
END = "#EC4899"         # ורוד
TRACK = "#262338"
BTN = "#8B5CF6"
BTN_HOVER = "#A07CFA"
BTN_OFF = "#3A3558"
FONT = "Segoe UI"


def lerp_color(c1: str, c2: str, t: float) -> str:
    """צבע באמצע הדרך בין שני צבעים (t בין 0 ל-1)."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(x + (y - x) * t):02x}" for x, y in zip(a, b))


def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class RoundButton(tk.Canvas):
    """כפתור מעוגל עם אפקט מעבר עכבר."""
    def __init__(self, parent, text, command, width=300, height=54):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0)
        self.w, self.h, self.command, self.enabled = width, height, command, True
        self.text = text
        self.draw(BTN)
        self.bind("<Enter>", lambda e: self.enabled and self.draw(BTN_HOVER))
        self.bind("<Leave>", lambda e: self.enabled and self.draw(BTN))
        self.bind("<Button-1>", lambda e: self.enabled and self.command())

    def draw(self, color):
        self.delete("all")
        rounded_rect(self, 2, 2, self.w - 2, self.h - 2, 26, fill=color, outline="")
        self.create_text(self.w / 2, self.h / 2, text=self.text, fill="white", font=(FONT, 14, "bold"))

    def set(self, text, enabled):
        self.text, self.enabled = text, enabled
        self.config(cursor="hand2" if enabled else "watch")
        self.draw(BTN if enabled else BTN_OFF)


class GlowBar(tk.Canvas):
    """פס התקדמות מעוגל: הצבע עובר מסגול לוורוד, עם ברק שזז לאורכו."""
    def __init__(self, parent, width=440, height=16):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0)
        self.w, self.h = width, height

    def draw(self, fraction: float, shimmer: float):
        self.delete("all")
        rounded_rect(self, 0, 0, self.w, self.h, self.h / 2, fill=TRACK, outline="")
        if fraction <= 0:
            return
        fill_w = max(self.h, self.w * fraction)
        rounded_rect(self, 0, 0, fill_w, self.h, self.h / 2,
                     fill=lerp_color(START, END, fraction), outline="")
        # ברק שזז בתוך החלק המלא
        sx = (shimmer % 1.0) * fill_w
        x1, x2 = max(2, sx - 30), min(fill_w - 2, sx)
        if x2 - x1 > 6:
            rounded_rect(self, x1, 3, x2, self.h - 3, 5,
                         fill=lerp_color(lerp_color(START, END, fraction), "#FFFFFF", 0.35), outline="")


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("סדרן ההורדות")
        root.geometry("520x660")
        root.configure(bg=BG)

        # ===== כותרת =====
        tk.Label(root, text="🧹", font=(FONT, 36), bg=BG, fg=TEXT).pack(pady=(24, 0))
        tk.Label(root, text="סדרן ההורדות", font=(FONT, 22, "bold"), fg=TEXT, bg=BG).pack()
        mode = "🧪 מצב ניסוי" if config.TEST_MODE else str(config.DOWNLOADS)
        tk.Label(root, text=mode, font=(FONT, 9), fg=MUTED, bg=BG).pack(pady=(2, 18))

        # ===== כפתור =====
        self.button = RoundButton(root, "✨  סדרי את ההורדות", self.start)
        self.button.pack(pady=(0, 22))

        # ===== פס התקדמות =====
        self.bar = GlowBar(root)
        self.bar.pack()
        row = tk.Frame(root, bg=BG)
        row.pack(fill="x", padx=40, pady=(6, 14))
        self.timer_label = tk.Label(row, text="", font=(FONT, 10), fg=MUTED, bg=BG)
        self.timer_label.pack(side="left")
        self.percent_label = tk.Label(row, text="", font=(FONT, 10, "bold"), fg=TEXT, bg=BG)
        self.percent_label.pack(side="right")

        # ===== כרטיס התוצאות =====
        card = tk.Frame(root, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        self.log = tk.Text(card, font=(FONT, 11), wrap="word", bg=CARD, fg=TEXT, relief="flat",
                           bd=0, padx=16, pady=14, spacing1=4, spacing3=4, insertbackground=TEXT)
        self.log.tag_configure("rtl", justify="right")
        self.log.tag_configure("muted", foreground=MUTED)
        self.log.tag_configure("done", foreground="#F9A8D4", font=(FONT, 12, "bold"))
        self.log.pack(fill="both", expand=True)
        self.write("לחצי על הכפתור, ואני אסדר הכול 💜", "muted")

        # ===== מצב =====
        self.queue = queue.Queue()
        self.run_config = None
        self.busy = False
        self.shown = 0.0       # כמה הפס מלא כרגע (מה שרואים)
        self.target = 0.0      # לאן הפס שואף
        self.cap = 0.0         # עד כמה מותר לו "לזחול" לבד בשלב הנוכחי
        self.shimmer = 0.0
        self.started_at = 0.0

        self.bar.draw(0, 0)
        root.after(30, self.animate)
        root.after(150, self.poll)

    # ===== עזרים =====
    def write(self, text: str, *tags):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n", ("rtl",) + tags)
        self.log.see("end")
        self.log.config(state="disabled")

    def stage(self, target: float, cap: float):
        self.target = max(self.target, target)
        self.cap = max(cap, self.target)

    # ===== אנימציה: הפס מתמלא בעדינות, והטיימר רץ =====
    def animate(self):
        if self.busy and self.target < self.cap:
            self.target = min(self.cap, self.target + 0.0006)   # זחילה איטית בזמן המתנה
        self.shown += (self.target - self.shown) * 0.08
        self.shimmer += 0.012
        self.bar.draw(self.shown, self.shimmer if self.busy else -1)
        if self.busy or self.shown > 0:
            self.percent_label.config(text=f"{int(round(self.shown * 100))}%")
        if self.busy:
            sec = int(time.time() - self.started_at)
            self.timer_label.config(text=f"⏱️ {sec // 60:02d}:{sec % 60:02d}")
        self.root.after(30, self.animate)

    # ===== הפעלה =====
    def start(self):
        self.busy = True
        self.started_at = time.time()
        self.shown = self.target = 0.0
        self.stage(0.04, 0.14)
        self.button.set("⏳  עובדת על זה...", False)
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self.write("📂 סורקת את ההורדות...", "muted")
        self.run_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        self.run_in_background({})

    def run_in_background(self, graph_input):
        """מריצים את הגרף ברקע עם stream, ומדווחים על כל תחנה שסיימה."""
        def work():
            try:
                for chunk in graph.stream(graph_input, self.run_config, stream_mode="updates"):
                    for node, update in chunk.items():
                        if node == "__interrupt__":
                            self.queue.put(("interrupt", update[0].value))
                            return
                        self.queue.put(("node", node, update or {}))
                self.queue.put(("done", graph.get_state(self.run_config).values))
            except Exception as e:
                self.queue.put(("error", str(e)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                kind = msg[0]
                if kind == "node":
                    self.on_node(msg[1], msg[2])
                elif kind == "interrupt":
                    self.ask_user(msg[1])
                elif kind == "done":
                    self.finish(msg[1])
                elif kind == "error":
                    self.write(f"❌ שגיאה: {msg[1]}")
                    self.end()
        except queue.Empty:
            pass
        self.root.after(150, self.poll)

    def on_node(self, node: str, update: dict):
        files = update.get("files", [])
        unsure = sum(1 for f in files if not f["confident"])
        if node == "scan_files":
            self.write(f"📂 מצאתי {len(files)} קבצים")
            self.stage(0.15, 0.50)
        elif node == "quick_classify":
            clear = len(files) - unsure
            msg = f"🏷️ מיינתי לפי השם: {clear} ברורים"
            if unsure:
                msg += f", {unsure} צריכים מבט מקרוב 👁️"
            self.write(msg)
            self.stage(0.55, 0.85)
        elif node == "deep_classify":
            self.write(f"👁️ הסתכלתי על התוכן. נשארו {unsure} לא ברורים")
            self.stage(min(0.88, self.target + 0.15), 0.9)
        elif node == "ask_user":
            self.stage(0.92, 0.97)
        elif node == "move_files":
            self.stage(1.0, 1.0)

    # ===== ✋ interrupt: חלון שאלה =====
    def ask_user(self, question: dict):
        self.write("🤔 יש קבצים שלא הצלחתי להחליט עליהם")
        self.cap = self.target  # הפס עוצר בזמן שמחכים לך
        win = tk.Toplevel(self.root)
        win.title("צריכה את עזרתך")
        win.configure(bg=BG)
        win.grab_set()

        tk.Label(win, text="🤔", font=(FONT, 28), bg=BG, fg=TEXT).pack(pady=(18, 0))
        tk.Label(win, text=question["question"], font=(FONT, 12, "bold"), fg=TEXT, bg=BG,
                 wraplength=420, justify="right").pack(pady=(4, 12), padx=20)

        choices = {}
        for f in question["files"]:
            box = tk.Frame(win, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            box.pack(fill="x", padx=20, pady=6)
            tk.Label(box, text=f"📄 {f['name']}", font=(FONT, 11, "bold"), fg=TEXT, bg=CARD,
                     anchor="e").pack(fill="x", padx=12, pady=(10, 0))
            tk.Label(box, text=f["reason"], font=(FONT, 9), fg=MUTED, bg=CARD, anchor="e",
                     wraplength=400, justify="right").pack(fill="x", padx=12)
            var = tk.StringVar(value="להשאיר")
            ttk.Combobox(box, textvariable=var, values=question["options"], state="readonly",
                         justify="right", font=(FONT, 10)).pack(fill="x", padx=12, pady=(6, 12))
            choices[f["name"]] = var

        def submit():
            answers = {name: var.get() for name, var in choices.items()}
            win.destroy()
            self.write("🙏 תודה! ממשיכה...", "muted")
            self.stage(self.target, 0.97)
            self.run_in_background(Command(resume=answers))

        RoundButton(win, "✓  אישור", submit, width=200, height=46).pack(pady=18)
        win.protocol("WM_DELETE_WINDOW", submit)  # סגירת החלון = להשאיר הכול

    # ===== סיום =====
    def finish(self, values: dict):
        self.stage(1.0, 1.0)
        moved = values.get("moved", [])
        if not moved:
            self.write("✨ אין מה לסדר, התיקייה כבר מסודרת!", "done")
        else:
            self.write(f"🎉 סיימתי! טיפלתי ב-{len(moved)} קבצים", "done")
            for line in moved:
                self.write(line)
        self.end()

    def end(self):
        self.busy = False
        self.button.set("✨  סדרי את ההורדות", True)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
