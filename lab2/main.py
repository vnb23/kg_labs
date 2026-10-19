import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk


class ImageProcessingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа 2 - Вариант 11")
        self.root.geometry("1000x600")

        self.original_image = None  # Исходное изображение (BGR для cv2)
        self.processed_image = None  # Обработанное изображение (BGR или Grayscale)

        self.setup_ui()

    def setup_ui(self):
        control_frame = tk.Frame(self.root, width=250, bg="#f0f0f0", padx=10, pady=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Button(control_frame, text="Загрузить изображение", command=self.load_image, width=25).pack(pady=5)

        tk.Label(control_frame, text="1. Поэлементные операции", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        tk.Button(control_frame, text="Линейное контрастирование", command=self.linear_contrast, width=25).pack(pady=2)
        tk.Button(control_frame, text="Негатив (инверсия)", command=self.negative, width=25).pack(pady=2)

        tk.Label(control_frame, text="2. Локальная пороговая", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(pady=(15, 5))

        # Настройки для локальной пороговой обработки
        tk.Label(control_frame, text="Размер окна (w):", bg="#f0f0f0").pack()
        self.window_size_var = tk.IntVar(value=15)
        tk.Entry(control_frame, textvariable=self.window_size_var, width=10).pack(pady=2)

        tk.Label(control_frame, text="Коэфф. k (Ниблэк: ~ -0.2, Саувола: ~0.5):", bg="#f0f0f0").pack()
        self.k_var = tk.DoubleVar(value=0.2)
        tk.Entry(control_frame, textvariable=self.k_var, width=10).pack(pady=2)

        tk.Button(control_frame, text="Метод Ниблэка", command=self.niblack_threshold, width=25).pack(pady=5)
        tk.Button(control_frame, text="Метод Сауволы", command=self.sauvola_threshold, width=25).pack(pady=2)

        tk.Button(control_frame, text="Сохранить результат", command=self.save_image, width=25, bg="#d9ecd0").pack(side=tk.BOTTOM, pady=20)

        image_frame = tk.Frame(self.root)
        image_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        tk.Label(image_frame, text="Оригинал:").grid(row=0, column=0, padx=10, pady=5)
        tk.Label(image_frame, text="Результат:").grid(row=0, column=1, padx=10, pady=5)

        self.canvas_orig = tk.Label(image_frame, text="Нет изображения", bg="gray", width=50, height=25)
        self.canvas_orig.grid(row=1, column=0, padx=10, pady=10)

        self.canvas_proc = tk.Label(image_frame, text="Нет изображения", bg="gray", width=50, height=25)
        self.canvas_proc.grid(row=1, column=1, padx=10, pady=10)

    def load_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if not filepath:
            return

        self.original_image = cv2.imread(filepath)
        self.processed_image = self.original_image.copy()

        self.display_image(self.original_image, self.canvas_orig)
        self.display_image(self.processed_image, self.canvas_proc)

    def save_image(self):
        if self.processed_image is None:
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if filepath:
            cv2.imwrite(filepath, self.processed_image)

    def display_image(self, cv_img, label_widget):
        # Масштабируем изображение для предпросмотра
        h, w = cv_img.shape[:2]
        max_size = 450
        scale = max_size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        
        resized_img = cv2.resize(cv_img, (new_w, new_h))
        
        if len(resized_img.shape) == 2: # Если Grayscale
            resized_img = cv2.cvtColor(resized_img, cv2.COLOR_GRAY2RGB)
        else: # Если BGR
            resized_img = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
            
        img_pil = Image.fromarray(resized_img)
        img_tk = ImageTk.PhotoImage(image=img_pil)

        label_widget.config(image=img_tk, text="", width=new_w, height=new_h)
        label_widget.image = img_tk

    # 1. Поэлементные операции и контрастирование
    def linear_contrast(self):
        if self.original_image is None: return
        
        # Линейное растяжение гистограммы (Min-Max)
        # Формула: P_new = (P_old - P_min) * (255 / (P_max - P_min))
        
        # Переводим в float для вычислений
        img_float = self.original_image.astype(np.float32)
        
        p_min = np.min(img_float)
        p_max = np.max(img_float)
        
        if p_max - p_min == 0:
            self.processed_image = self.original_image.copy()
        else:
            stretched = (img_float - p_min) * (255.0 / (p_max - p_min))
            self.processed_image = np.clip(stretched, 0, 255).astype(np.uint8)
            
        self.display_image(self.processed_image, self.canvas_proc)

    def negative(self):
        if self.original_image is None: return
        
        # Поэлементная операция: Инверсия
        self.processed_image = 255 - self.original_image
        self.display_image(self.processed_image, self.canvas_proc)

    # 2. Локальная пороговая обработка
    def calc_local_stats(self, gray_img, w_size):
        # Оптимизированный расчет локального среднего и локального ст. отклонения
        img_float = gray_img.astype(np.float32)

        # Локальное среднее (mu)
        mu = cv2.blur(img_float, (w_size, w_size))

        # Локальное среднее квадратов
        mu_sq = cv2.blur(img_float**2, (w_size, w_size))

        # Дисперсия = E[X^2] - (E[X])^2
        variance = mu_sq - mu**2
        variance[variance < 0] = 0 # Защита от ошибок округления (отрицательных корней)

        # Локальное стандартное отклонение (sigma)
        sigma = np.sqrt(variance)

        return mu, sigma

    def niblack_threshold(self):
        if self.original_image is None:
            return
        try:
            w = self.window_size_var.get()
            k = self.k_var.get()
        except Exception:
            messagebox.showerror("Ошибка", "Неверный формат параметров")
            return

        # Локальная обработка применяется к изображению в оттенках серого
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        mu, sigma = self.calc_local_stats(gray, w)

        # Формула Ниблэка: T = mu + k * sigma
        T = mu + k * sigma

        # Бинаризация: если пиксель > T, то 255 (белый), иначе 0 (черный)
        binary = np.zeros_like(gray)
        binary[gray > T] = 255

        self.processed_image = binary
        self.display_image(self.processed_image, self.canvas_proc)

    def sauvola_threshold(self):
        if self.original_image is None:
            return
        try:
            w = self.window_size_var.get()
            k = self.k_var.get()
        except Exception:
            messagebox.showerror("Ошибка", "Неверный формат параметров")
            return

        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        mu, sigma = self.calc_local_stats(gray, w)

        R = 128.0 # Максимальное значение стандартного отклонения для 8-битного серого

        # Формула Сауволы: T = mu * [1 + k * (sigma / R - 1)]
        T = mu * (1 + k * (sigma / R - 1.0))
        binary = np.zeros_like(gray)
        binary[gray > T] = 255

        self.processed_image = binary
        self.display_image(self.processed_image, self.canvas_proc)


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessingApp(root)
    root.mainloop()