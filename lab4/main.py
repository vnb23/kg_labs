"""
Лабораторная работа 4. Алгоритмы отсечения отрезков и многоугольников.
Вариант 11:
  Часть 1 - алгоритм Лианга-Барски (параметрическое задание отрезков);
  Часть 2 - алгоритм отсечения выпуклого многоугольника
            (Сазерленд-Ходжман, прямоугольное окно).

Запуск:
  python clipping.py                      # откроется окно с выбором файлов
  python clipping.py segments.txt polygon.txt
  python clipping.py segments.txt polygon.txt --save out.png

Формат файла отрезков:
  n
  x1 y1 x2 y2        (n строк)
  xmin ymin xmax ymax

Формат файла многоугольника:
  m
  x y                (m вершин, обход по или против часовой стрелки)
  xmin ymin xmax ymax
"""
import argparse
import sys

import matplotlib

# Ввод данных


def read_numbers(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # поддержка комментариев после '#' и запятых как разделителей
    lines = [ln.split("#")[0] for ln in text.splitlines()]
    return [float(t) for t in " ".join(lines).replace(",", " ").split()]


def read_segments(path):
    nums = read_numbers(path)
    n = int(nums[0])
    if len(nums) != 1 + 4 * n + 4:
        raise ValueError(
            f"Ожидалось {1 + 4 * n + 4} чисел, получено {len(nums)} (n={n})")
    segs = []
    for i in range(n):
        x1, y1, x2, y2 = nums[1 + 4 * i: 5 + 4 * i]
        segs.append(((x1, y1), (x2, y2)))
    xmin, ymin, xmax, ymax = nums[1 + 4 * n:]
    return segs, normalize_window(xmin, ymin, xmax, ymax)


def read_polygon(path):
    nums = read_numbers(path)
    m = int(nums[0])
    if len(nums) != 1 + 2 * m + 4:
        raise ValueError(
            f"Ожидалось {1 + 2 * m + 4} чисел, получено {len(nums)} (m={m})")
    poly = [(nums[1 + 2 * i], nums[2 + 2 * i]) for i in range(m)]
    xmin, ymin, xmax, ymax = nums[1 + 2 * m:]
    return poly, normalize_window(xmin, ymin, xmax, ymax)


def normalize_window(xmin, ymin, xmax, ymax):
    return (min(xmin, xmax), min(ymin, ymax), max(xmin, xmax), max(ymin, ymax))


# Часть 1. Алгоритм Лианга-Барски


def liang_barsky(p1, p2, window):
    """
    Отсечение отрезка P1P2 прямоугольным окном.
    Отрезок: P(t) = P1 + t*(P2-P1), t in [0, 1].
    Условия видимости: p_k * t <= q_k, k = 1..4:
        p1 = -dx, q1 = x1 - xmin   (левая граница)
        p2 =  dx, q2 = xmax - x1   (правая граница)
        p3 = -dy, q3 = y1 - ymin   (нижняя граница)
        p4 =  dy, q4 = ymax - y1   (верхняя граница)
    Возвращает (A, B) - видимую часть или None, если отрезок невидим.
    """
    xmin, ymin, xmax, ymax = window
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1

    p = (-dx, dx, -dy, dy)
    q = (x1 - xmin, xmax - x1, y1 - ymin, ymax - y1)

    t0, t1 = 0.0, 1.0
    for pk, qk in zip(p, q):
        if pk == 0:
            # отрезок параллелен границе; если снаружи - отбрасываем
            if qk < 0:
                return None
        else:
            t = qk / pk
            if pk < 0:          # вход в окно
                if t > t1:
                    return None
                t0 = max(t0, t)
            else:               # выход из окна
                if t < t0:
                    return None
                t1 = min(t1, t)
    if t0 > t1:
        return None
    return (x1 + t0 * dx, y1 + t0 * dy), (x1 + t1 * dx, y1 + t1 * dy)

def clip_polygon(poly, window):
    """
    Последовательное отсечение многоугольника каждой из четырёх границ окна.
    Для каждого ребра (S -> E) относительно границы возможны 4 случая:
      S внутри, E внутри   -> выводим E
      S внутри, E снаружи  -> выводим точку пересечения
      S снаружи, E снаружи -> ничего
      S снаружи, E внутри  -> выводим точку пересечения и E
    Для выпуклого многоугольника результат - один выпуклый многоугольник.
    """
    xmin, ymin, xmax, ymax = window

    def inter_x(s, e, xb):
        t = (xb - s[0]) / (e[0] - s[0])
        return (xb, s[1] + t * (e[1] - s[1]))

    def inter_y(s, e, yb):
        t = (yb - s[1]) / (e[1] - s[1])
        return (s[0] + t * (e[0] - s[0]), yb)

    edges = [
        (lambda p: p[0] >= xmin, lambda s, e: inter_x(s, e, xmin)),
        (lambda p: p[0] <= xmax, lambda s, e: inter_x(s, e, xmax)),
        (lambda p: p[1] >= ymin, lambda s, e: inter_y(s, e, ymin)),
        (lambda p: p[1] <= ymax, lambda s, e: inter_y(s, e, ymax)),
    ]

    out = list(poly)
    for inside, intersect in edges:
        if not out:
            break
        inp, out = out, []
        s = inp[-1]
        for e in inp:
            if inside(e):
                if not inside(s):
                    out.append(intersect(s, e))
                out.append(e)
            elif inside(s):
                out.append(intersect(s, e))
            s = e
    return out


def is_convex(poly):
    """Проверка выпуклости (знак векторного произведения соседних рёбер)."""
    n = len(poly)
    if n < 3:
        return False
    sign = 0
    for i in range(n):
        a, b, c = poly[i], poly[(i + 1) % n], poly[(i + 2) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if cr != 0:
            s = 1 if cr > 0 else -1
            if sign == 0:
                sign = s
            elif s != sign:
                return False
    return True


# Визуализация

COL_WINDOW = "tab:blue"
COL_SOURCE = "tab:red"
COL_VISIBLE = "tab:green"


def setup_axes(ax, points, window, title):
    xs = [p[0] for p in points] + [window[0], window[2]]
    ys = [p[1] for p in points] + [window[1], window[3]]
    pad = 0.1 * max(max(xs) - min(xs), max(ys) - min(ys), 1)
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, linestyle=":", linewidth=0.6)
    ax.axhline(0, color="black", linewidth=1)   # ось X
    ax.axvline(0, color="black", linewidth=1)   # ось Y
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(title)


def draw_window(ax, window):
    from matplotlib.patches import Rectangle
    xmin, ymin, xmax, ymax = window
    ax.add_patch(Rectangle((xmin, ymin), xmax - xmin, ymax - ymin,
                           fill=False, edgecolor=COL_WINDOW, linewidth=2,
                           label="Отсекающее окно"))


def draw_segments(ax, segs, window):
    from matplotlib.lines import Line2D
    points = [p for s in segs for p in s]
    setup_axes(ax, points, window, "Часть 1. Алгоритм Лианга-Барски")
    draw_window(ax, window)
    for (a, b) in segs:
        ax.plot([a[0], b[0]], [a[1], b[1]], color=COL_SOURCE,
                linestyle="--", linewidth=1.2)
    results = []
    for (a, b) in segs:
        r = liang_barsky(a, b, window)
        results.append(r)
        if r:
            ax.plot([r[0][0], r[1][0]], [r[0][1], r[1][1]],
                    color=COL_VISIBLE, linewidth=3)
    ax.legend(handles=[
        Line2D([], [], color=COL_WINDOW, lw=2, label="Окно"),
        Line2D([], [], color=COL_SOURCE, lw=1.2, ls="--", label="Исходные отрезки"),
        Line2D([], [], color=COL_VISIBLE, lw=3, label="Видимые части"),
    ], loc="best", fontsize=8)
    return results


def draw_polygon(ax, poly, window):
    from matplotlib.patches import Polygon
    from matplotlib.lines import Line2D
    setup_axes(ax, poly, window, "Часть 2. Отсечение выпуклого многоугольника")
    draw_window(ax, window)
    ax.add_patch(Polygon(poly, closed=True, fill=False, edgecolor=COL_SOURCE,
                         linestyle="--", linewidth=1.2))
    res = clip_polygon(poly, window)
    if len(res) >= 3:
        ax.add_patch(Polygon(res, closed=True, facecolor=COL_VISIBLE,
                             alpha=0.35, edgecolor=COL_VISIBLE, linewidth=3))
    ax.legend(handles=[
        Line2D([], [], color=COL_WINDOW, lw=2, label="Окно"),
        Line2D([], [], color=COL_SOURCE, lw=1.2, ls="--", label="Исходный многоугольник"),
        Line2D([], [], color=COL_VISIBLE, lw=3, label="Видимая часть"),
    ], loc="best", fontsize=8)
    return res


def run(seg_path, poly_path, save=None, show=True):
    import matplotlib.pyplot as plt

    segs, win1 = read_segments(seg_path)
    poly, win2 = read_polygon(poly_path)

    if not is_convex(poly):
        print("Предупреждение: многоугольник не выпуклый, "
              "результат алгоритма может быть некорректным.", file=sys.stderr)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.5))
    res_segs = draw_segments(ax1, segs, win1)
    res_poly = draw_polygon(ax2, poly, win2)
    fig.tight_layout()

    print("=== Часть 1: Лианг-Барски ===")
    for i, ((a, b), r) in enumerate(zip(segs, res_segs), 1):
        if r:
            print(f"{i}: {a}-{b} -> ({r[0][0]:.3f}, {r[0][1]:.3f})-"
                  f"({r[1][0]:.3f}, {r[1][1]:.3f})")
        else:
            print(f"{i}: {a}-{b} -> невидим")
    print("=== Часть 2: отсечение многоугольника ===")
    if res_poly:
        print("Вершины результата:",
              [(round(x, 3), round(y, 3)) for x, y in res_poly])
    else:
        print("Многоугольник полностью вне окна")

    if save:
        fig.savefig(save, dpi=150)
        print("Сохранено в", save)
    if show:
        plt.show()


def pick_files_gui():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    seg = filedialog.askopenfilename(title="Файл с отрезками")
    if not seg:
        sys.exit(0)
    poly = filedialog.askopenfilename(title="Файл с многоугольником")
    if not poly:
        sys.exit(0)
    root.destroy()
    return seg, poly


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("segments", nargs="?")
    ap.add_argument("polygon", nargs="?")
    ap.add_argument("--save", help="сохранить картинку в файл (без окна)")
    args = ap.parse_args()

    if args.save:
        matplotlib.use("Agg")
    if not (args.segments and args.polygon):
        args.segments, args.polygon = pick_files_gui()
    run(args.segments, args.polygon, save=args.save, show=not args.save)


if __name__ == "__main__":
    main()