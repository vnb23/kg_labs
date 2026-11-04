from math import floor


def rnd(v):
    """Округление «половина вверх»."""
    return floor(v + 0.5)


def _sign(v):
    return 1 if v > 0 else -1 if v < 0 else 0


# 1. Пошаговый алгоритм: y = k*x + b
def step_by_step(x1, y1, x2, y2, trace=None):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        if trace is not None:
            trace.append([0, x1, y1, "—", y1])
        return [(x1, y1)]
    pts = []
    if abs(dx) >= abs(dy): # пологая линия: шагаем по x
        k = dy / dx
        b = y1 - k * x1
        s = _sign(dx)
        for i, x in enumerate(range(x1, x2 + s, s)):
            y = k * x + b
            yr = rnd(y)
            pts.append((x, yr))
            if trace is not None:
                trace.append([i, x, f"{k:.4f}·{x}+{b:.4f} = {y:.4f}", yr])
    else: # крутая линия: шагаем по y, x = k'*y + b'
        k = dx / dy
        b = x1 - k * y1
        s = _sign(dy)
        for i, y in enumerate(range(y1, y2 + s, s)):
            x = k * y + b
            xr = rnd(x)
            pts.append((xr, y))
            if trace is not None:
                trace.append([i, f"{k:.4f}·{y}+{b:.4f} = {x:.4f}", y, xr])
    return pts


STEP_COLUMNS_FLAT = ["i", "x", "y = k·x + b", "y округл."]
STEP_COLUMNS_STEEP = ["i", "x = k·y + b", "y", "x округл."]

# 2. Алгоритм ЦДА (DDA)
def dda(x1, y1, x2, y2, trace=None):
    dx, dy = x2 - x1, y2 - y1
    length = max(abs(dx), abs(dy))
    if length == 0:
        if trace is not None:
            trace.append([0, x1, y1, x1, y1])
        return [(x1, y1)]
    sx, sy = dx / length, dy / length      # приращения по осям за шаг
    x, y = float(x1), float(y1)
    pts = []
    for i in range(length + 1):
        px, py = rnd(x), rnd(y)
        pts.append((px, py))
        if trace is not None:
            trace.append([i, f"{x:.4f}", f"{y:.4f}", px, py])
        x += sx
        y += sy
    return pts


DDA_COLUMNS = ["i", "x", "y", "X = round(x)", "Y = round(y)"]


# 3. Алгоритм Брезенхема (отрезок, целочисленный, все октанты)
def bresenham_line(x1, y1, x2, y2, trace=None):
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx, sy = (1 if x2 >= x1 else -1), (1 if y2 >= y1 else -1)
    steep = dy > dx
    if steep: # главная ось — y
        dx, dy = dy, dx
    err = 2 * dy - dx
    x, y = x1, y1
    pts = []
    for i in range(dx + 1):
        pts.append((x, y))
        if trace is not None:
            trace.append([i, x, y, err, "по диагонали" if err >= 0 else "по главной оси"])
        if err >= 0:
            if steep:
                x += sx
            else:
                y += sy
            err -= 2 * dx
        if steep:
            y += sy
        else:
            x += sx
        err += 2 * dy
    return pts


BRES_COLUMNS = ["i", "x", "y", "ошибка d", "шаг (d ≥ 0 ?)"]


# 4. Алгоритм Брезенхема для окружности

def bresenham_circle(cx, cy, r, trace=None):
    seen = {}
    x, y = 0, r
    d = 3 - 2 * r
    i = 0
    while x <= y:
        octant = [(cx + x, cy + y), (cx - x, cy + y), (cx + x, cy - y), (cx - x, cy - y),
                  (cx + y, cy + x), (cx - y, cy + x), (cx + y, cy - x), (cx - y, cy - x)]
        for p in octant:
            seen[p] = None
        if trace is not None:
            trace.append([i, x, y, d, f"({x},{y}) → 8 точек"])
        if d < 0:
            d += 4 * x + 6
        else:
            d += 4 * (x - y) + 10
            y -= 1
        x += 1
        i += 1
    return list(seen)


CIRCLE_COLUMNS = ["i", "x", "y", "d", "симметричные точки"]


# Дополнительно: алгоритм Кастла–Питвея
def _center_phase(word, dx, dy):
    """Циклически сдвигает сбалансированное слово так, чтобы отрезок проходил
    по центру «коридора» пикселей (ошибка в обе стороны < 0.5). За O(n), в целых числах:
    E_i = (число D в первых i буквах)*dx - i*dy; выбираем сдвиг с E_j ближе всего к середине диапазона."""
    E, c = [0], 0
    for i, ch in enumerate(word, 1):
        c += ch == "D"
        E.append(c * dx - i * dy)
    mid = max(E) + min(E)
    j = min(range(len(word)), key=lambda t: abs(2 * E[t] - mid))
    return word[j:] + word[:j]


def castle_pitteway(x1, y1, x2, y2, trace=None, log=None):
    """Строит отрезок «евклидовым» алгоритмом над строками шагов.

    Для 0 < dy < dx имеем dx-dy шагов S (по главной оси) и dy шагов D (по диагонали).
    Пара (x, y) = (число S, число D) обрабатывается как в алгоритме Евклида,
    а строки m1="S", m2="D" склеиваются: x>y -> m2=m1+m2, x-=y; иначе m1=m1+m2, y-=x.
    Когда x==y, результат — (m1+m2) повторённое x раз; затем фаза слова центрируется.
    """
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx, sy = (1 if x2 >= x1 else -1), (1 if y2 >= y1 else -1)
    steep = dy > dx
    if steep:
        dx, dy = dy, dx
    ns, nd = dx - dy, dy
    if nd == 0:
        word = "S" * ns
    elif ns == 0:
        word = "D" * nd
    else:
        x, y, m1, m2 = ns, nd, "S", "D"
        while x != y:
            if log is not None:
                log.append([x, y, m1, m2])
            if x > y:
                x -= y
                m2 = m1 + m2
            else:
                y -= x
                m1 = m1 + m2
        if log is not None:
            log.append([x, y, m1, m2])
        word = (m1 + m2) * x
        word = _center_phase(word, dx, dy)
    px, py = x1, y1
    pts = [(px, py)]
    if trace is not None:
        trace.append([0, "—", px, py])
    for i, ch in enumerate(word, 1):
        if ch == "D":
            px += sx
            py += sy
        elif steep:
            py += sy
        else:
            px += sx
        pts.append((px, py))
        if trace is not None:
            trace.append([i, ch, px, py])
    return pts, word


CP_COLUMNS = ["i", "шаг (S/D)", "x", "y"]
CP_LOG_COLUMNS = ["x (S)", "y (D)", "m1", "m2"]


# Дополнительно B: сглаживание (алгоритм Ву)
def wu_line(x1, y1, x2, y2, trace=None):
    """Возвращает [(x, y, яркость 0..1)]. Яркость = площадь «покрытия» пикселя линией."""
    steep = abs(y2 - y1) > abs(x2 - x1)
    if steep:
        x1, y1, x2, y2 = y1, x1, y2, x2
    if x1 > x2:
        x1, y1, x2, y2 = x2, y2, x1, y1
    dx, dy = x2 - x1, y2 - y1
    k = dy / dx if dx else 0.0
    pts = []
    for i, x in enumerate(range(x1, x2 + 1)):
        y = y1 + k * (x - x1)
        lo = floor(y)
        f = y - lo
        for yy, a in ((lo, 1 - f), (lo + 1, f)):
            if a > 1e-9:
                pts.append((yy, x, a) if steep else (x, yy, a))
        if trace is not None:
            trace.append([i, x, f"{y:.4f}", f"{1 - f:.3f}", f"{f:.3f}"])
    return pts


WU_COLUMNS = ["i", "x", "y точное", "яркость нижнего", "яркость верхнего"]


# интерфейс
import time
import tkinter as tk
from tkinter import ttk

ALGOS = {
    "Пошаговый": "step", "ЦДА": "dda", "Брезенхем (отрезок)": "bres",
    "Брезенхем (окружность)": "circle", "Кастл–Питвей (доп.)": "cp", "Ву — сглаживание (доп.)": "wu",
}
FORMULAS = {
    "step": "k = Δy/Δx;  b = y₁ − k·x₁;  y = k·x + b;  пиксель (x, round y).  Если |Δy| > |Δx|, роли x и y меняются.",
    "dda": "L = max(|Δx|,|Δy|);  sx = Δx/L;  sy = Δy/L;  x += sx;  y += sy;  пиксель (round x, round y).",
    "bres": "d₀ = 2Δy − Δx;  если d ≥ 0: шаг по обеим осям и d −= 2Δx;  всегда d += 2Δy.  (Δ — по модулю, главная ось — длиннейшая.)",
    "circle": "x=0, y=R, d₀ = 3 − 2R;  d<0: d += 4x+6;  иначе d += 4(x−y)+10, y−−;  x++ пока x ≤ y;  8 симметричных точек.",
    "cp": "Евклид над строками шагов: x>y → m2=m1+m2, x−=y;  иначе m1=m1+m2, y−=x;  слово=(m1+m2)^x, фаза центрируется.",
    "wu": "y = y₁ + k(x−x₁);  яркость нижнего пикселя = 1 − frac(y), верхнего = frac(y).",
}
COLUMNS = {
    "step": STEP_COLUMNS_FLAT, "dda": DDA_COLUMNS, "bres": BRES_COLUMNS,
    "circle": CIRCLE_COLUMNS, "cp": CP_COLUMNS, "wu": WU_COLUMNS,
}

# палитра
BG, PANEL, INK, MUTED, LINE = "#f4f5f7", "#ffffff", "#1d2330", "#667085", "#d9dde5"
ACCENT, PIXEL, IDEAL, HILITE = "#2457d6", (36, 87, 214), "#d92d20", "#f79009"


def mix(rgb, a):
    """Смешивает цвет с белым: a=1 — полный цвет, a=0 — белый."""
    return "#%02x%02x%02x" % tuple(round(255 - (255 - c) * a) for c in rgb)


def measure(f, args, budget=0.05, repeats=5):
    """Среднее время одного вызова в мкс (лучшая из серий)."""
    f(*args)
    t0 = time.perf_counter(); f(*args); once = time.perf_counter() - t0
    n = max(1, int(budget / max(once, 1e-7)))
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter_ns()
        for _ in range(n):
            f(*args)
        best = min(best, (time.perf_counter_ns() - t0) / n)
    return best / 1000.0, n


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Базовые растровые алгоритмы")
        self.geometry("1320x820")
        self.minsize(980, 640)
        self.configure(bg=BG)
        self.cell, self.cx, self.cy = 30.0, 5.0, 2.0
        self.points, self.alpha, self.params = [], [], None
        self.sel = -1
        self.click_state = 0
        self._drag = None
        self._moved = False
        self._style()
        self._build()
        self.after(100, self.run)


    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", background=PANEL, foreground=INK, font=("Segoe UI", 10))
        s.configure("TFrame", background=PANEL)
        s.configure("TLabel", background=PANEL, foreground=INK)
        s.configure("Muted.TLabel", foreground=MUTED, font=("Segoe UI", 9))
        s.configure("H.TLabel", font=("Segoe UI", 13, "bold"))
        s.configure("Sec.TLabel", foreground=MUTED, font=("Segoe UI", 8, "bold"))
        s.configure("TCheckbutton", background=PANEL)
        s.configure("TEntry", padding=5, fieldbackground="#fff", bordercolor=LINE)
        s.configure("TCombobox", padding=5, fieldbackground="#fff", bordercolor=LINE)
        s.configure("Accent.TButton", background=ACCENT, foreground="#fff", padding=8, borderwidth=0, font=("Segoe UI", 10, "bold"))
        s.map("Accent.TButton", background=[("active", "#1c45ad")])
        s.configure("TButton", padding=4)
        s.configure("Treeview", rowheight=22, fieldbackground="#fff", bordercolor=LINE, font=("Consolas", 10))
        s.configure("Treeview.Heading", background="#f2f4f7", font=("Segoe UI", 9, "bold"), relief="flat")
        s.map("Treeview", background=[("selected", "#fff1c2")], foreground=[("selected", INK)])

    def _build(self):
        side = ttk.Frame(self, padding=16)
        side.pack(side="left", fill="y")
        ttk.Label(side, text="Базовые растровые\nалгоритмы", style="H.TLabel").pack(anchor="w", pady=(0, 12))

        ttk.Label(side, text="АЛГОРИТМ", style="Sec.TLabel").pack(anchor="w")
        self.algo = tk.StringVar(value="Брезенхем (отрезок)")
        cb = ttk.Combobox(side, textvariable=self.algo, values=list(ALGOS), state="readonly", width=28)
        cb.pack(fill="x", pady=(2, 10))
        cb.bind("<<ComboboxSelected>>", lambda e: self._algo_changed())

        self.v = {k: tk.StringVar(value=str(d)) for k, d in
                  dict(x1=0, y1=0, x2=10, y2=4, cx=0, cy=0, r=8).items()}
        self.line_box = self._fields(side, "КОНЦЫ ОТРЕЗКА", [("x₁", "x1"), ("y₁", "y1"), ("x₂", "x2"), ("y₂", "y2")])
        self.circle_box = self._fields(side, "ОКРУЖНОСТЬ", [("центр x", "cx"), ("центр y", "cy"), ("радиус R", "r")])
        self.line_box.pack(fill="x")

        ttk.Button(side, text="Построить", style="Accent.TButton", command=self.run).pack(fill="x", pady=(12, 4))
        self.err = ttk.Label(side, text="", foreground="#b42318", wraplength=250)
        self.err.pack(anchor="w")

        ttk.Label(side, text="ОТОБРАЖЕНИЕ", style="Sec.TLabel").pack(anchor="w", pady=(14, 2))
        self.show_ideal = tk.BooleanVar(value=True)
        self.show_centers = tk.BooleanVar(value=True)
        self.show_coords = tk.BooleanVar(value=True)
        for text, var in (("Идеальная линия (красная)", self.show_ideal),
                          ("Центры пикселей", self.show_centers),
                          ("Координаты пикселей (крупный масштаб)", self.show_coords)):
            ttk.Checkbutton(side, text=text, variable=var, command=self.draw).pack(anchor="w")

        ttk.Label(side, text="КАК КООРДИНАТЫ ПРИВЯЗАНЫ К СЕТКЕ", style="Sec.TLabel").pack(anchor="w", pady=(14, 2))
        ttk.Label(side, style="Muted.TLabel", wraplength=255, justify="left", text=(
            "Целое число (x, y) — это ЦЕНТР пикселя. Пиксель — квадрат [x−½, x+½]×[y−½, y+½], "
            "поэтому линии сетки идут по полуцелым значениям, а оси и подписи — через центры пикселей. "
            "Ось Y направлена вверх.\n\nКолесо — масштаб, перетаскивание — сдвиг, клик — задать точку.")).pack(anchor="w")

        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        top = tk.Frame(right, bg=BG)
        top.pack(fill="both", expand=True)
        self.cv = tk.Canvas(top, bg="#fff", highlightthickness=0, cursor="crosshair")
        self.cv.pack(fill="both", expand=True)
        self.hover = tk.Label(self.cv, text="пиксель: —", bg="#ffffff", fg=INK, font=("Segoe UI", 9), bd=1, relief="solid", padx=6)
        self.hover.place(x=10, y=10)
        zb = tk.Frame(self.cv, bg="#fff", bd=1, relief="solid")
        zb.place(relx=1.0, x=-10, y=10, anchor="ne")
        tk.Label(zb, text="Масштаб", bg="#fff", font=("Segoe UI", 9)).pack(side="left", padx=(6, 2))
        self.zoom = tk.Scale(zb, from_=4, to=80, orient="horizontal", showvalue=False, length=130, bg="#fff",
                             highlightthickness=0, command=self._zoom_slider)
        self.zoom.set(30)
        self.zoom.pack(side="left")
        ttk.Button(zb, text="Вписать", command=self.fit).pack(side="left", padx=6, pady=3)

        bottom = ttk.Frame(right)
        bottom.pack(fill="x")
        bottom.configure(height=250)
        bottom.pack_propagate(False)
        info = ttk.Frame(bottom, padding=10, width=380)
        info.pack(side="right", fill="y")
        info.pack_propagate(False)
        self.info = tk.Text(info, wrap="word", bg=PANEL, fg=INK, relief="flat", font=("Segoe UI", 10), width=1, height=1)
        self.info.pack(fill="both", expand=True)
        self.info.tag_configure("b", font=("Segoe UI", 10, "bold"))
        self.info.tag_configure("m", font=("Consolas", 10), background="#f2f4f7")
        tf = ttk.Frame(bottom)
        tf.pack(side="left", fill="both", expand=True)
        self.tree = ttk.Treeview(tf, show="headings", selectmode="browse")
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._row_selected)

        c = self.cv
        c.bind("<Configure>", lambda e: self.draw())
        c.bind("<MouseWheel>", lambda e: self._wheel(e, 1 if e.delta > 0 else -1))
        c.bind("<Button-4>", lambda e: self._wheel(e, 1))
        c.bind("<Button-5>", lambda e: self._wheel(e, -1))
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._motion_drag)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<Motion>", self._motion)
        self.bind("<Return>", lambda e: self.run())

    def _fields(self, parent, title, items):
        box = ttk.Frame(parent)
        ttk.Label(box, text=title, style="Sec.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        for i, (label, key) in enumerate(items):
            r, c = divmod(i, 2)
            f = ttk.Frame(box)
            f.grid(row=r + 1, column=c, sticky="ew", padx=(0 if c == 0 else 6, 0), pady=3)
            ttk.Label(f, text=label, style="Muted.TLabel").pack(anchor="w")
            ttk.Entry(f, textvariable=self.v[key], width=11).pack(fill="x")
        box.columnconfigure((0, 1), weight=1)
        return box

    def _algo_changed(self):
        circle = ALGOS[self.algo.get()] == "circle"
        (self.line_box if circle else self.circle_box).pack_forget()
        (self.circle_box if circle else self.line_box).pack(fill="x", before=self._run_button_anchor())
        self.click_state = 0
        self.run()

    def _run_button_anchor(self):
        # кнопка «Построить» — первый ttk.Button в боковой панели
        for w in self.line_box.master.pack_slaves():
            if isinstance(w, ttk.Button):
                return w

    def W(self): return max(self.cv.winfo_width(), 2)
    def H(self): return max(self.cv.winfo_height(), 2)
    def sx(self, x): return self.W() / 2 + (x - self.cx) * self.cell
    def sy(self, y): return self.H() / 2 - (y - self.cy) * self.cell
    def wx(self, px): return (px - self.W() / 2) / self.cell + self.cx
    def wy(self, py): return -(py - self.H() / 2) / self.cell + self.cy

    def run(self):
        self.err.config(text="")
        key = ALGOS[self.algo.get()]
        try:
            g = lambda k: int(self.v[k].get())
            if key == "circle":
                args = (g("cx"), g("cy"), g("r"))
                if args[2] < 0:
                    raise ValueError("Радиус должен быть ≥ 0")
            else:
                args = (g("x1"), g("y1"), g("x2"), g("y2"))
            if any(abs(a) > 400 for a in args):
                raise ValueError("Координаты по модулю не более 400")
        except ValueError as e:
            msg = str(e)
            self.err.config(text=msg if "Радиус" in msg or "Координаты" in msg else "Введите целые числа")
            return
        trace, extra, alpha = [], "", []
        if key == "step":
            pts = step_by_step(*args, trace=trace)
            cols = STEP_COLUMNS_FLAT if abs(args[2] - args[0]) >= abs(args[3] - args[1]) else STEP_COLUMNS_STEEP
            f = step_by_step
        elif key == "dda":
            pts, cols, f = dda(*args, trace=trace), DDA_COLUMNS, dda
        elif key == "bres":
            pts, cols, f = bresenham_line(*args, trace=trace), BRES_COLUMNS, bresenham_line
        elif key == "circle":
            pts, cols, f = bresenham_circle(*args, trace=trace), CIRCLE_COLUMNS, bresenham_circle
        elif key == "cp":
            log = []
            pts, word = castle_pitteway(*args, trace=trace, log=log)
            cols, f = CP_COLUMNS, castle_pitteway
            extra = "Слово шагов (S — по главной оси, D — по диагонали):\n" + word + "\n\nИтерации Евклида:\n" + \
                    "\n".join(f"x={a}  y={b}  m1={c}  m2={d}" for a, b, c, d in log) + "\n\n"
        else:
            wu = wu_line(*args, trace=trace)
            pts, alpha = [(x, y) for x, y, _ in wu], [a for _, _, a in wu]
            cols, f = WU_COLUMNS, wu_line
            extra = "Яркость пикселя = площадь, покрытая линией (показана насыщенностью цвета).\n\n"
        t_us, reps = measure(f, args)
        self.points, self.alpha, self.params, self.sel = pts, alpha, (key, args), -1

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="e", width=max(70, 12 * len(c)), stretch=True)
        for r in trace:
            self.tree.insert("", "end", values=r)

        self.info.config(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("end", "Формулы\n", "b")
        self.info.insert("end", FORMULAS[key] + "\n\n")
        if key == "circle":
            self.info.insert("end", f"Окружность: центр ({args[0]}, {args[1]}), R = {args[2]}; пикселей: {len(pts)}\n\n")
        else:
            self.info.insert("end", f"Отрезок: ({args[0]}, {args[1]}) → ({args[2]}, {args[3]});  "
                                    f"Δx = {args[2]-args[0]}, Δy = {args[3]-args[1]};  пикселей: {len(pts)}\n\n")
        self.info.insert("end", extra)
        self.info.insert("end", "Время работы\n", "b")
        self.info.insert("end", f"{t_us:.3f} мкс на вызов (среднее по {reps} повторам, без вывода трассы)")
        self.info.config(state="disabled")
        self.fit()

    def fit(self):
        if not self.points:
            return self.draw()
        xs, ys = [p[0] for p in self.points], [p[1] for p in self.points]
        self.cx, self.cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        w, h = max(max(xs) - min(xs) + 3, 1), max(max(ys) - min(ys) + 3, 1)
        self.cell = float(max(4, min(80, int(min((self.W() - 90) / w, (self.H() - 70) / h)))))
        self.zoom.set(self.cell)
        self.draw()

    def draw(self):
        c = self.cv
        c.delete("all")
        w, h, cell = self.W(), self.H(), self.cell
        x0, x1 = int(self.wx(0)) - 2, int(self.wx(w)) + 2
        y0, y1 = int(self.wy(h)) - 2, int(self.wy(0)) + 2

        # пиксели
        for i, (x, y) in enumerate(self.points):
            a = self.alpha[i] if self.alpha else 1.0
            c.create_rectangle(self.sx(x - .5), self.sy(y + .5), self.sx(x + .5), self.sy(y - .5),
                               fill=mix(PIXEL, a), outline="")
        if 0 <= self.sel < len(self.points):
            x, y = self.points[self.sel]
            c.create_rectangle(self.sx(x - .5) + 1, self.sy(y + .5) + 1, self.sx(x + .5) - 1, self.sy(y - .5) - 1,
                               outline=HILITE, width=3)

        if cell >= 6:
            for x in range(x0, x1 + 1):
                c.create_line(self.sx(x - .5), 0, self.sx(x - .5), h, fill=LINE)
            for y in range(y0, y1 + 1):
                c.create_line(0, self.sy(y + .5), w, self.sy(y + .5), fill=LINE)

        # оси
        ox, oy = self.sx(0), self.sy(0)
        c.create_line(0, oy, w - 4, oy, fill=INK, width=2, arrow="last", arrowshape=(10, 12, 4))
        c.create_line(ox, h, ox, 4, fill=INK, width=2, arrow="last", arrowshape=(10, 12, 4))
        c.create_text(w - 14, oy - 12, text="x", font=("Segoe UI", 11, "bold"), fill=INK)
        c.create_text(ox + 12, 14, text="y", font=("Segoe UI", 11, "bold"), fill=INK)

        # подписи
        step = next((s for s in (1, 2, 5, 10, 20, 50, 100) if s * cell >= 34), 100)
        ly = min(max(oy + 14, 14), h - 8)
        lx = min(max(ox - 8, 20), w - 6)
        for x in range((x0 // step) * step, x1 + 1, step):
            if x == 0:
                continue
            px = self.sx(x)
            c.create_line(px, oy - 3, px, oy + 3, fill=INK)
            c.create_text(px, ly, text=str(x), fill="#475467", font=("Segoe UI", 8))
        for y in range((y0 // step) * step, y1 + 1, step):
            py = self.sy(y)
            c.create_line(ox - 3, py, ox + 3, py, fill=INK)
            c.create_text(lx, py, text=str(y), fill="#475467", font=("Segoe UI", 8), anchor="e")
        c.create_text(lx, ly, text="0", fill="#475467", font=("Segoe UI", 8), anchor="e")

        if self.params and self.show_ideal.get():
            key, a = self.params
            if key == "circle":
                r = a[2] * cell
                c.create_oval(self.sx(a[0]) - r, self.sy(a[1]) - r, self.sx(a[0]) + r, self.sy(a[1]) + r, outline=IDEAL, width=2)
            else:
                c.create_line(self.sx(a[0]), self.sy(a[1]), self.sx(a[2]), self.sy(a[3]), fill=IDEAL, width=2)

        show_c, show_t = self.show_centers.get() and cell >= 10, self.show_coords.get() and cell >= 38
        for i, (x, y) in enumerate(self.points):
            if show_c:
                c.create_oval(self.sx(x) - 2.5, self.sy(y) - 2.5, self.sx(x) + 2.5, self.sy(y) + 2.5, fill="#fff", outline="")
            if show_t:
                c.create_text(self.sx(x), self.sy(y) + cell / 2 - 7, text=f"{x},{y}", fill="#fff" if (not self.alpha or self.alpha[i] > .5) else INK,
                              font=("Segoe UI", 8))
        self.hover.lift()


    def _zoom_slider(self, val):
        if abs(float(val) - self.cell) > 0.01:
            self.cell = float(val)
            self.draw()

    def _wheel(self, e, direction):
        bx, by = self.wx(e.x), self.wy(e.y)
        self.cell = min(80.0, max(3.0, self.cell * (1.15 if direction > 0 else 1 / 1.15)))
        self.cx += bx - self.wx(e.x)
        self.cy += by - self.wy(e.y)
        self.zoom.set(self.cell)
        self.draw()

    def _press(self, e):
        self._drag, self._moved = (e.x, e.y, self.cx, self.cy), False

    def _motion_drag(self, e):
        if not self._drag:
            return
        dx, dy = e.x - self._drag[0], e.y - self._drag[1]
        if abs(dx) + abs(dy) > 3:
            self._moved = True
        if self._moved:
            self.cx, self.cy = self._drag[2] - dx / self.cell, self._drag[3] + dy / self.cell
            self.draw()

    def _release(self, e):
        if self._drag and not self._moved:                       # клик — задать точку
            x, y = round(self.wx(e.x)), round(self.wy(e.y))
            if ALGOS[self.algo.get()] == "circle":
                if self.click_state == 0:
                    self.v["cx"].set(x); self.v["cy"].set(y); self.click_state = 1
                else:
                    self.v["r"].set(round(((x - int(self.v["cx"].get())) ** 2 + (y - int(self.v["cy"].get())) ** 2) ** .5))
                    self.click_state = 0; self.run()
            else:
                if self.click_state == 0:
                    self.v["x1"].set(x); self.v["y1"].set(y); self.click_state = 1
                else:
                    self.v["x2"].set(x); self.v["y2"].set(y); self.click_state = 0; self.run()
        self._drag = None

    def _motion(self, e):
        self.hover.config(text=f"пиксель: ({round(self.wx(e.x))}, {round(self.wy(e.y))})    точка: ({self.wx(e.x):.2f}, {self.wy(e.y):.2f})")

    def _row_selected(self, _):
        s = self.tree.selection()
        self.sel = self.tree.index(s[0]) if s else -1
        self.draw()


if __name__ == "__main__":
    App().mainloop()