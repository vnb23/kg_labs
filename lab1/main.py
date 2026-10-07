import tkinter as tk
from tkinter import ttk, colorchooser
import colorsys

try:
    from PIL import Image, ImageTk
except ImportError:
    import tkinter.messagebox as mb
    root = tk.Tk()
    root.withdraw()
    mb.showerror("Ошибка", "Для работы палитры нужна библиотека Pillow.")
    exit()


def clamp(val, min_val, max_val):
    """Вспомогательная функция для удержания значения в пределах [min_val, max_val]"""
    return max(min_val, min(max_val, val))


class ColorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа 1: Цветовые модели (CMYK - RGB - HLS)")

        # Задаем стартовый размер и минимальные ограничения окна
        self.root.geometry("950x550")
        self.root.minsize(950, 550)

        # Включаем тему для виджетов
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        self.updating = False
        self.current_rgb = (255, 0, 0)  # По умолчанию красный
        self.vars = {'RGB': {}, 'CMYK': {}, 'HLS': {}}

        # Регистрация функции валидации для Entry
        self.vcmd = self.root.register(self.validate_entry_input)

        # Динамические размеры палитры
        self.palette_width = 400
        self.palette_height = 200
        self.base_palette_img = None  # Кэш изображения для быстрого растягивания
        self.bg_image_id = None

        self.build_ui()
        self.update_all_from_rgb()

    def validate_entry_input(self, P, max_val):
        """
        Проверка ввода в текстовое поле на лету:
        P - текущее предполагаемое значение текстового поля
        max_val - максимальное допустимое значение для данного поля
        """
        # Разрешаем пустое поле (чтобы пользователь мог стереть цифру и ввести новую)
        if P == "":
            return True

        # Проверяем, что введены только цифры
        if not P.isdigit():
            return False

        # Ограничиваем длину ввода (не больше 3 символов)
        if len(P) > 3:
            return False

        # Проверяем верхнюю границу
        try:
            val = int(P)
            if val > int(max_val):
                return False
        except ValueError:
            return False

        return True

    def on_entry_focus_out(self, var):
        """Если поле оставлено пустым при потере фокуса, устанавливаем 0"""
        try:
            var.get()
        except tk.TclError:
            var.set(0)

    def build_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Левая часть: Палитра и предпросмотр
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        ttk.Label(left_frame, text="Интерактивная палитра (Тон / Светлота)",
                  font=('Arial', 10, 'bold')).pack(anchor="w", pady=(0, 5))

        self.palette_canvas = tk.Canvas(left_frame, highlightthickness=1, highlightbackground="#ccc", cursor="crosshair")
        self.palette_canvas.pack(fill=tk.BOTH, expand=True)
        self.palette_canvas.bind("<Button-1>", self.on_palette_click)
        self.palette_canvas.bind("<B1-Motion>", self.on_palette_drag)
        self.palette_canvas.bind("<Configure>", self.on_canvas_resize)

        # Курсор на палитре
        r = 6
        self.cursor_id = self.palette_canvas.create_oval(-r, -r, r, r, outline='black', width=2)
        self.cursor_inner_id = self.palette_canvas.create_oval(-r+1, -r+1, r-1, r-1, outline='white', width=1)

        # Предпросмотр цвета
        self.color_preview = tk.Canvas(left_frame, height=40, highlightthickness=1, highlightbackground="#ccc")
        self.color_preview.pack(fill=tk.X, pady=15)

        ttk.Button(left_frame, text="Выбрать цвет из системной палитры",
                   command=self.choose_color).pack(fill=tk.X)

        # Правая часть: Ползунки
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")

        # Создаем блоки моделей
        self.create_model_frame(right_frame, 'RGB', ['R', 'G', 'B'],
                                [(0, 255), (0, 255), (0, 255)], self.on_rgb_change)
        self.create_model_frame(right_frame, 'CMYK', ['C', 'M', 'Y', 'K'],
                                [(0, 100), (0, 100), (0, 100), (0, 100)], self.on_cmyk_change)
        self.create_model_frame(right_frame, 'HLS', ['H', 'L', 'S'],
                                [(0, 360), (0, 100), (0, 100)], self.on_hls_change)

    def create_model_frame(self, parent, model_name, components, ranges, callback):
        frame = ttk.LabelFrame(parent, text=model_name)
        frame.pack(fill=tk.X, pady=(0, 10), ipady=2, ipadx=5)
        frame.columnconfigure(1, weight=1)

        for i, (comp, (min_val, max_val)) in enumerate(zip(components, ranges)):
            ttk.Label(frame, text=comp, font=('Arial', 10, 'bold'), width=2).grid(row=i, column=0, padx=5, pady=5)

            var = tk.IntVar()
            self.vars[model_name][comp] = var
            var.trace_add('write', lambda *args, cb=callback: cb())

            slider = ttk.Scale(frame, from_=min_val, to=max_val, orient=tk.HORIZONTAL, variable=var)
            slider.grid(row=i, column=1, padx=10, pady=5, sticky="ew")

            # Включаем валидацию для текстового поля ввода
            entry = ttk.Entry(
                frame, 
                textvariable=var, 
                width=5, 
                justify='center',
                validate='key',
                validatecommand=(self.vcmd, '%P', str(max_val))
            )
            entry.grid(row=i, column=2, padx=5, pady=5)
            # При потере фокуса заполняем пустое значение нулевым
            entry.bind("<FocusOut>", lambda e, v=var: self.on_entry_focus_out(v))

    def on_canvas_resize(self, event):
        if event.width > 10 and event.height > 10:
            self.palette_width = event.width
            self.palette_height = event.height
            self.update_palette_display()
            self.update_cursor_from_vars()

    def generate_base_palette(self):
        if self.base_palette_img is not None:
            return

        w, h = 360, 100
        pixels = bytearray(w * h * 3)

        l_vals = [1.0 - (y / h) for y in range(h)]
        h_vals = [x / w for x in range(w)]

        idx = 0
        for l in l_vals:
            for hue in h_vals:
                r, g, b = colorsys.hls_to_rgb(hue, l, 1.0)
                pixels[idx] = int(r * 255)
                pixels[idx+1] = int(g * 255)
                pixels[idx+2] = int(b * 255)
                idx += 3

        self.base_palette_img = Image.frombytes('RGB', (w, h), bytes(pixels))
        self.update_palette_display()

    def update_palette_display(self):
        if not self.base_palette_img or self.palette_width < 10:
            return

        img_resized = self.base_palette_img.resize((self.palette_width, self.palette_height), Image.BILINEAR)
        self.palette_photo = ImageTk.PhotoImage(img_resized)

        if self.bg_image_id is None:
            self.bg_image_id = self.palette_canvas.create_image(0, 0, image=self.palette_photo, anchor="nw")
        else:
            self.palette_canvas.itemconfig(self.bg_image_id, image=self.palette_photo)

        self.palette_canvas.tag_raise(self.cursor_id)
        self.palette_canvas.tag_raise(self.cursor_inner_id)

    def on_palette_click(self, event):
        self.update_from_palette(event.x, event.y)

    def on_palette_drag(self, event):
        self.update_from_palette(event.x, event.y)

    def update_from_palette(self, x, y):
        # Ограничиваем клики строго границами Canvas
        x = clamp(x, 0, self.palette_width)
        y = clamp(y, 0, self.palette_height)

        hue = x / self.palette_width
        lightness = 1.0 - (y / self.palette_height)

        saturation = self.vars['HLS']['S'].get() / 100.0
        if saturation == 0:
            saturation = 1.0
            self.vars['HLS']['S'].set(100)

        if self.updating:
            return
        self.updating = True

        r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
        self.current_rgb = (clamp(int(r * 255), 0, 255),
                            clamp(int(g * 255), 0, 255),
                            clamp(int(b * 255), 0, 255))

        self.updating = False
        self.update_all_from_rgb()

    def update_cursor_from_vars(self):
        try:
            h = clamp(self.vars['HLS']['H'].get(), 0, 360) / 360.0
            l = clamp(self.vars['HLS']['L'].get(), 0, 100) / 100.0
            self.update_cursor_position(h, l)
        except tk.TclError:
            pass

    def update_cursor_position(self, h, l):
        x = h * self.palette_width
        y = (1.0 - l) * self.palette_height
        r = 6
        self.palette_canvas.coords(self.cursor_id, x-r, y-r, x+r, y+r)
        self.palette_canvas.coords(self.cursor_inner_id, x-r+1, y-r+1, x+r-1, y+r-1)

    def choose_color(self):
        initial = f"#{self.current_rgb[0]:02x}{self.current_rgb[1]:02x}{self.current_rgb[2]:02x}"
        color = colorchooser.askcolor(initialcolor=initial, title="Выберите цвет")
        if color[0]:
            self.current_rgb = (clamp(int(color[0][0]), 0, 255),
                                clamp(int(color[0][1]), 0, 255),
                                clamp(int(color[0][2]), 0, 255))
            self.update_all_from_rgb()

    def on_rgb_change(self):
        if self.updating:
            return
        try:
            r = clamp(self.vars['RGB']['R'].get(), 0, 255)
            g = clamp(self.vars['RGB']['G'].get(), 0, 255)
            b = clamp(self.vars['RGB']['B'].get(), 0, 255)
            
            # Корректируем переменные, если они вышли за границы при вводе
            if self.vars['RGB']['R'].get() != r: self.vars['RGB']['R'].set(r)
            if self.vars['RGB']['G'].get() != g: self.vars['RGB']['G'].set(g)
            if self.vars['RGB']['B'].get() != b: self.vars['RGB']['B'].set(b)

            self.current_rgb = (r, g, b)
            self.update_ui(exclude='RGB')
        except tk.TclError:
            pass

    def on_cmyk_change(self):
        if self.updating:
            return
        try:
            c_val = clamp(self.vars['CMYK']['C'].get(), 0, 100)
            m_val = clamp(self.vars['CMYK']['M'].get(), 0, 100)
            y_val = clamp(self.vars['CMYK']['Y'].get(), 0, 100)
            k_val = clamp(self.vars['CMYK']['K'].get(), 0, 100)

            c = c_val / 100.0
            m = m_val / 100.0
            y = y_val / 100.0
            k = k_val / 100.0

            r = clamp(int(round(255 * (1 - c) * (1 - k))), 0, 255)
            g = clamp(int(round(255 * (1 - m) * (1 - k))), 0, 255)
            b = clamp(int(round(255 * (1 - y) * (1 - k))), 0, 255)

            self.current_rgb = (r, g, b)
            self.update_ui(exclude='CMYK')
        except tk.TclError:
            pass

    def on_hls_change(self):
        if self.updating:
            return
        try:
            h_val = clamp(self.vars['HLS']['H'].get(), 0, 360)
            l_val = clamp(self.vars['HLS']['L'].get(), 0, 100)
            s_val = clamp(self.vars['HLS']['S'].get(), 0, 100)

            h = h_val / 360.0
            l = l_val / 100.0
            s = s_val / 100.0

            r, g, b = colorsys.hls_to_rgb(h, l, s)

            self.current_rgb = (clamp(int(round(r * 255)), 0, 255),
                                clamp(int(round(g * 255)), 0, 255),
                                clamp(int(round(b * 255)), 0, 255))
            self.update_ui(exclude='HLS')
        except tk.TclError:
            pass

    def update_all_from_rgb(self):
        self.update_ui(exclude=None)

    def update_ui(self, exclude):
        self.updating = True
        r, g, b = [clamp(val, 0, 255) for val in self.current_rgb]

        # Превью цвета
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        self.color_preview.config(bg=hex_color)

        # RGB
        if exclude != 'RGB':
            self.vars['RGB']['R'].set(r)
            self.vars['RGB']['G'].set(g)
            self.vars['RGB']['B'].set(b)

        # CMYK
        if exclude != 'CMYK':
            r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
            k = 1 - max(r_norm, g_norm, b_norm)
            if k >= 1.0:
                c = m = y = 0
            else:
                c = (1 - r_norm - k) / (1 - k)
                m = (1 - g_norm - k) / (1 - k)
                y = (1 - b_norm - k) / (1 - k)
            self.vars['CMYK']['C'].set(clamp(int(round(c * 100)), 0, 100))
            self.vars['CMYK']['M'].set(clamp(int(round(m * 100)), 0, 100))
            self.vars['CMYK']['Y'].set(clamp(int(round(y * 100)), 0, 100))
            self.vars['CMYK']['K'].set(clamp(int(round(k * 100)), 0, 100))

        # HLS
        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        if exclude != 'HLS':
            if s == 0 and 'H' in self.vars['HLS']:
                h = self.vars['HLS']['H'].get() / 360.0
            self.vars['HLS']['H'].set(clamp(int(round(h * 360)), 0, 360))
            self.vars['HLS']['L'].set(clamp(int(round(l * 100)), 0, 100))
            self.vars['HLS']['S'].set(clamp(int(round(s * 100)), 0, 100))

        self.generate_base_palette()
        self.update_cursor_position(h, l)

        self.updating = False


root = tk.Tk()
app = ColorApp(root)
root.mainloop()