import tkinter as tk
from tkinter import filedialog, messagebox
import os

import cv2
import numpy as np
from PIL import Image, ImageTk


class ImageProcessingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа 2 - Вариант 11")
        self.root.geometry("1500x900")
        self.root.minsize(1100, 750)  # минимальный размер окна

        self.original_image = None   # BGR
        self.processed_image = None  # BGR или Grayscale

        self.setup_ui()

    def setup_ui(self):
        bg = "#f0f0f0"
        control = tk.Frame(self.root, width=280, bg=bg, padx=10, pady=8)
        control.pack(side=tk.LEFT, fill=tk.Y)

        def header(text):
            tk.Label(control, text=text, bg=bg, font=("Arial", 10, "bold")).pack(pady=(12, 3))

        def param(text, var, width=8):
            row = tk.Frame(control, bg=bg)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=text, bg=bg, anchor="w").pack(side=tk.LEFT)
            tk.Entry(row, textvariable=var, width=width).pack(side=tk.RIGHT)

        def button(text, cmd, **kw):
            tk.Button(control, text=text, command=cmd, width=28, **kw).pack(pady=2)

        button("Загрузить изображение", self.load_image)
        button("Сбросить результат", self.reset_result)

        # 1. Поэлементные операции
        header("1. Поэлементные операции")
        self.per_channel_var = tk.BooleanVar(value=True)
        self.clip_var = tk.DoubleVar(value=0.0)
        tk.Checkbutton(control, text="Контрастировать по каналам", variable=self.per_channel_var,
                       bg=bg).pack(anchor="w")
        param("Отсечение перцентилей, % (0 = min-max):", self.clip_var, 6)
        button("Линейное контрастирование", self.linear_contrast)
        button("Негатив (инверсия)", self.negative)

        self.bright_var = tk.DoubleVar(value=30)
        self.alpha_var = tk.DoubleVar(value=1.3)
        self.gamma_var = tk.DoubleVar(value=0.7)
        param("Яркость c (+c):", self.bright_var)
        button("Изменить яркость", self.brightness)
        param("Контраст a (×a):", self.alpha_var)
        button("Изменить контраст", self.contrast)
        param("Гамма γ:", self.gamma_var)
        button("Гамма-коррекция", self.gamma_correction)
        button("Логарифмическое преобразование", self.log_transform)

        # 2. Локальная пороговая
        header("2. Пороговая обработка")
        self.window_size_var = tk.IntVar(value=15)
        self.k_niblack_var = tk.DoubleVar(value=-0.2)
        self.k_sauvola_var = tk.DoubleVar(value=0.5)
        param("Размер окна w (нечётный):", self.window_size_var)
        param("k Ниблэка (≈ -0.2):", self.k_niblack_var)
        param("k Сауволы (≈ 0.5):", self.k_sauvola_var)
        button("Метод Ниблэка", self.niblack_threshold)
        button("Метод Сауволы", self.sauvola_threshold)
        button("Глобальный порог Оцу (для сравнения)", self.otsu_threshold)

        tk.Button(control, text="Сохранить результат", command=self.save_image,
                  width=28, bg="#d9ecd0").pack(side=tk.BOTTOM, pady=12)

        # Изображения и гистограммы
        image_frame = tk.Frame(self.root)
        image_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        image_frame.grid_columnconfigure(0, weight=1, uniform="img")
        image_frame.grid_columnconfigure(1, weight=1, uniform="img")
        image_frame.grid_rowconfigure(1, weight=1)

        tk.Label(image_frame, text="Оригинал:").grid(row=0, column=0, padx=10, pady=5)
        self.result_title = tk.Label(image_frame, text="Результат:")
        self.result_title.grid(row=0, column=1, padx=10, pady=5)

        # Изображения показываются в реальном размере (масштаб 1:1).
        # Если картинка больше области просмотра - появляются полосы прокрутки.
        self.canvas_orig = self.make_view(image_frame, 0)
        self.canvas_proc = self.make_view(image_frame, 1)

        tk.Label(image_frame, text="Гистограмма оригинала").grid(row=2, column=0)
        tk.Label(image_frame, text="Гистограмма результата").grid(row=2, column=1)
        self.hist_orig = tk.Label(image_frame)
        self.hist_orig.grid(row=3, column=0, padx=10, pady=5)
        self.hist_proc = tk.Label(image_frame)
        self.hist_proc.grid(row=3, column=1, padx=10, pady=5)

    @staticmethod
    def make_view(parent, column):
        frame = tk.Frame(parent)
        frame.grid(row=1, column=column, padx=10, pady=5, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(frame, bg="#f0f0f0", width=300, height=300, highlightthickness=0)
        vbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        hbar = tk.Scrollbar(frame, orient=tk.HORIZONTAL, command=canvas.xview)
        canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")

        canvas.create_text(150, 150, text="Нет изображения", fill="gray", tags="placeholder")
        return canvas

    def has_image(self):
        if self.original_image is None:
            messagebox.showwarning("Нет изображения", "Сначала загрузите изображение")
            return False
        return True

    def get_params(self, *vars_):
        try:
            return [v.get() for v in vars_]
        except tk.TclError:
            messagebox.showerror("Ошибка", "Неверный формат параметров")
            return None

    def set_result(self, img, title="Результат:"):
        self.processed_image = img
        self.result_title.config(text=title)
        self.refresh_result()

    def refresh_result(self):
        self.display_image(self.processed_image, self.canvas_proc)
        self.show_hist(self.processed_image, self.hist_proc)

    @staticmethod
    def to_photo(cv_img):
        if cv_img.ndim == 2:
            rgb = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        return ImageTk.PhotoImage(image=Image.fromarray(rgb))

    def display_image(self, cv_img, canvas):
        """Показывает изображение в натуральном размере (без масштабирования)."""
        h, w = cv_img.shape[:2]
        img_tk = self.to_photo(cv_img)
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=img_tk)
        canvas.image = img_tk
        canvas.configure(scrollregion=(0, 0, w, h))
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

    def put_on_label(self, cv_img, label_widget):
        img_tk = self.to_photo(cv_img)
        label_widget.config(image=img_tk, text="")
        label_widget.image = img_tk

    @staticmethod
    def make_hist_image(img, w=600, h=250):
        canvas = np.full((h, w, 3), 255, np.uint8)
        if img.ndim == 2:
            channels = [(img, (0, 0, 0))]
        else:
            channels = [(img[:, :, 0], (255, 0, 0)),
                        (img[:, :, 1], (0, 160, 0)),
                        (img[:, :, 2], (0, 0, 255))]
        hists = [cv2.calcHist([ch], [0], None, [256], [0, 256]).flatten() for ch, _ in channels]
        peak = max(hh.max() for hh in hists) or 1.0
        
        xs = np.linspace(0, w - 1, 256)
        for hh, (_, color) in zip(hists, channels):
            ys = (h - 1) - hh / peak * (h - 10)
            pts = np.stack([xs, ys], axis=1).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(canvas, [pts], False, color, 2, cv2.LINE_AA) # Можно поменять толщину линии с 1 на 2, чтобы на большой гистограмме было лучше видно
        return canvas

    def show_hist(self, img, label_widget):
        self.put_on_label(self.make_hist_image(img), label_widget)

    @staticmethod
    def read_image(path):
        """Читает изображение в BGR. Сначала OpenCV (imdecode + fromfile - работают
        кириллические пути), затем запасной путь через Pillow (AVIF, WebP и др.)."""
        img = None
        try:
            data = np.fromfile(path, dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception:
            img = None
        if img is None:
            try:
                try:
                    import pillow_avif  # noqa: F401  (плагин для старых версий Pillow)
                except ImportError:
                    pass
                pil = Image.open(path).convert("RGB")
                img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
            except Exception:
                img = None
        return img

    def load_image(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.avif *.webp")])
        if not filepath:
            return
        img = self.read_image(filepath)
        if img is None:
            messagebox.showerror("Ошибка", "Не удалось открыть файл")
            return

        self.original_image = img
        self.display_image(self.original_image, self.canvas_orig)
        self.show_hist(self.original_image, self.hist_orig)
        self.set_result(self.original_image.copy())

    def reset_result(self):
        if not self.has_image():
            return
        self.set_result(self.original_image.copy())

    def save_image(self):
        if self.processed_image is None:
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not filepath:
            return
        ext = os.path.splitext(filepath)[1] or ".png"
        ok, buf = cv2.imencode(ext, self.processed_image)
        if not ok:
            messagebox.showerror("Ошибка", "Не удалось сохранить файл")
            return
        buf.tofile(filepath)

    #1. Поэлементные операции
    @staticmethod
    def stretch(channel, p_clip):
        """Линейное растяжение: (P - Pmin) * 255 / (Pmax - Pmin)."""
        ch = channel.astype(np.float64)
        if p_clip > 0:
            p_min, p_max = np.percentile(ch, [p_clip, 100 - p_clip])
        else:
            p_min, p_max = ch.min(), ch.max()
        if p_max - p_min < 1e-9:
            return channel.copy()
        out = (ch - p_min) * (255.0 / (p_max - p_min))
        return np.clip(out, 0, 255).astype(np.uint8)

    def linear_contrast(self):
        if not self.has_image():
            return
        params = self.get_params(self.clip_var)
        if params is None:
            return
        p_clip = params[0]
        if not (0 <= p_clip < 50):
            messagebox.showerror("Ошибка", "Перцентиль должен быть в диапазоне [0; 50)")
            return

        img = self.original_image
        if self.per_channel_var.get():
            out = np.dstack([self.stretch(img[:, :, c], p_clip) for c in range(3)])
            title = "Результат: линейное контрастирование (по каналам)"
        else:
            # растягиваем только яркость (V в HSV), цвет не искажается
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            hsv[:, :, 2] = self.stretch(hsv[:, :, 2], p_clip)
            out = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            title = "Результат: линейное контрастирование (по яркости)"
        self.set_result(out, title)

    def negative(self):
        if not self.has_image():
            return
        self.set_result(255 - self.original_image, "Результат: негатив")

    def brightness(self):
        if not self.has_image():
            return
        params = self.get_params(self.bright_var)
        if params is None:
            return
        out = np.clip(self.original_image.astype(np.float64) + params[0], 0, 255).astype(np.uint8)
        self.set_result(out, "Результат: яркость")

    def contrast(self):
        if not self.has_image():
            return
        params = self.get_params(self.alpha_var)
        if params is None:
            return
        out = np.clip(self.original_image.astype(np.float64) * params[0], 0, 255).astype(np.uint8)
        self.set_result(out, "Результат: контраст")

    def gamma_correction(self):
        if not self.has_image():
            return
        params = self.get_params(self.gamma_var)
        if params is None:
            return
        gamma = params[0]
        if gamma <= 0:
            messagebox.showerror("Ошибка", "Гамма должна быть > 0")
            return
        lut = (255.0 * (np.arange(256) / 255.0) ** gamma).clip(0, 255).astype(np.uint8)
        self.set_result(cv2.LUT(self.original_image, lut), "Результат: гамма-коррекция")

    def log_transform(self):
        if not self.has_image():
            return
        c = 255.0 / np.log(256.0)
        lut = (c * np.log1p(np.arange(256))).clip(0, 255).astype(np.uint8)
        self.set_result(cv2.LUT(self.original_image, lut), "Результат: логарифмическое преобразование")

    # 2. Пороговая обработка
    @staticmethod
    def calc_local_stats(gray_img, w_size):
        img = gray_img.astype(np.float64)
        mu = cv2.blur(img, (w_size, w_size))
        mu_sq = cv2.blur(img * img, (w_size, w_size))
        variance = np.maximum(mu_sq - mu * mu, 0)
        return mu, np.sqrt(variance)

    def get_window(self):
        params = self.get_params(self.window_size_var)
        if params is None:
            return None
        w = params[0]
        if w < 3:
            messagebox.showerror("Ошибка", "Размер окна должен быть не меньше 3")
            return None
        if w % 2 == 0:
            w += 1
            self.window_size_var.set(w)
        return w

    def niblack_threshold(self):
        if not self.has_image():
            return
        w = self.get_window()
        params = self.get_params(self.k_niblack_var)
        if w is None or params is None:
            return
        k = params[0]

        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        mu, sigma = self.calc_local_stats(gray, w)
        T = mu + k * sigma  # Ниблэк

        binary = np.where(gray > T, 255, 0).astype(np.uint8)
        self.set_result(binary, f"Результат: Ниблэк (w={w}, k={k})")

    def sauvola_threshold(self):
        if not self.has_image():
            return
        w = self.get_window()
        params = self.get_params(self.k_sauvola_var)
        if w is None or params is None:
            return
        k = params[0]

        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        mu, sigma = self.calc_local_stats(gray, w)
        R = 128.0
        T = mu * (1 + k * (sigma / R - 1.0))  # Саувола

        binary = np.where(gray > T, 255, 0).astype(np.uint8)
        self.set_result(binary, f"Результат: Саувола (w={w}, k={k})")

    def otsu_threshold(self):
        if not self.has_image():
            return
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        t, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        self.set_result(binary, f"Результат: глобальный порог Оцу (T={t:.0f})")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessingApp(root)
    root.mainloop()