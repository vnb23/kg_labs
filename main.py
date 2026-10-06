import tkinter as tk
from tkinter import ttk, colorchooser
import colorsys

try:
    from PIL import Image, ImageTk
except ImportError:
    import tkinter.messagebox as mb
    root = tk.Tk()
    root.withdraw()
    mb.showerror("Ошибка", "Для работы палитры нужна библиотека Pillow.\nУстановите её командой:\npip install pillow")
    exit()


class ColorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа 1: Цветовые модели (CMYK - RGB - HLS)")

        # Задаем стартовый размер и минимальные ограничения окна
        self.root.geometry("900x450")
        self.root.minsize(700, 350)

        # Включаем тему для виджетов
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        self.updating = False
        self.current_rgb = (255, 0, 0)  # По умолчанию красный
        self.vars = {'RGB': {}, 'CMYK': {}, 'HLS': {}}

        # Динамические размеры палитры
        self.palette_width = 400
        self.palette_height = 200
        self._last_s = -1.0
        self.base_palette_img = None  # Кэш изображения для быстрого растягивания
        self.bg_image_id = None

        self.build_ui()
        self.update_all_from_rgb()

    def build_ui(self):
        # Главный контейнер (расширяется во все стороны)
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Разделяем на 2 колонки: левая (палитра) и правая (ползунки)
        main_frame.columnconfigure(0, weight=1)  # Левая колонка тянется
        main_frame.columnconfigure(1, weight=1)  # Правая колонка тянется
        main_frame.rowconfigure(0, weight=1)

        # Левая часть: Палитра и предпросмотр
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        ttk.Label(left_frame, text="Интерактивная палитра (Тон / Светлота)",
                  font=('Arial', 10, 'bold')).pack(anchor="w", pady=(0, 5))

        # Холст для градиента (expand=True позволяет ему занимать все свободное место)
        self.palette_canvas = tk.Canvas(left_frame, highlightthickness=1, highlightbackground="#ccc", cursor="crosshair")
        self.palette_canvas.pack(fill=tk.BOTH, expand=True)
        # Привязка событий мыши к палитре
        self.palette_canvas.bind("<Button-1>", self.on_palette_click)
        self.palette_canvas.bind("<B1-Motion>", self.on_palette_drag)
        # Привязка события изменения размера холста
        self.palette_canvas.bind("<Configure>", self.on_canvas_resize)

        # Курсор на палитре
        r = 6
        self.cursor_id = self.palette_canvas.create_oval(-r, -r, r, r, outline='black', width=2)
        self.cursor_inner_id = self.palette_canvas.create_oval(-r+1, -r+1, r-1, r-1, outline='white', width=1)

        # Предпросмотр цвета
        self.color_preview = tk.Canvas(left_frame, height=40, highlightthickness=1, highlightbackground="#ccc")
        self.color_preview.pack(fill=tk.X, pady=15)  # fill=tk.X растягивает по горизонтали

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

        # Настраиваем колонку 1 (где ползунок), чтобы она растягивалась
        frame.columnconfigure(1, weight=1)

        for i, (comp, (min_val, max_val)) in enumerate(zip(components, ranges)):
            ttk.Label(frame, text=comp, font=('Arial', 10, 'bold'), width=2).grid(row=i, column=0, padx=5, pady=5)

            var = tk.IntVar()
            self.vars[model_name][comp] = var
            var.trace_add('write', lambda *args, cb=callback: cb())

            # sticky="ew" заставляет ползунок тянуться от края до края (East-West)
            slider = ttk.Scale(frame, from_=min_val, to=max_val, orient=tk.HORIZONTAL, variable=var)
            slider.grid(row=i, column=1, padx=10, pady=5, sticky="ew")

            entry = ttk.Entry(frame, textvariable=var, width=5, justify='center')
            entry.grid(row=i, column=2, padx=5, pady=5)

    def on_canvas_resize(self, event):
        """Вызывается при изменении размеров окна (и холста)"""
        if event.width > 10 and event.height > 10:
            self.palette_width = event.width
            self.palette_height = event.height
            self.update_palette_display()
            self.update_cursor_from_vars()

    def generate_base_palette(self, saturation):
        """Создает картинку палитры небольшого фиксированного размера для кэша"""
        if abs(self._last_s - saturation) < 0.01 and self.base_palette_img is not None:
            return

        self._last_s = saturation
        w, h = 360, 100  # Разрешение базовой картинки
        pixels = bytearray(w * h * 3)

        l_vals = [1.0 - (y / h) for y in range(h)]
        h_vals = [x / w for x in range(w)]

        idx = 0
        for l in l_vals:
            for hue in h_vals:
                r, g, b = colorsys.hls_to_rgb(hue, l, saturation)
                pixels[idx] = int(r * 255)
                pixels[idx+1] = int(g * 255)
                pixels[idx+2] = int(b * 255)
                idx += 3

        self.base_palette_img = Image.frombytes('RGB', (w, h), bytes(pixels))
        self.update_palette_display()

    def update_palette_display(self):
        """Быстро растягивает базовую картинку до текущих размеров окна"""
        if not self.base_palette_img or self.palette_width < 10:
            return

        # Image.NEAREST или Image.BILINEAR - работает очень быстро
        img_resized = self.base_palette_img.resize((self.palette_width, self.palette_height), Image.BILINEAR)
        self.palette_photo = ImageTk.PhotoImage(img_resized)

        if self.bg_image_id is None:
            self.bg_image_id = self.palette_canvas.create_image(0, 0, image=self.palette_photo, anchor="nw")
        else:
            self.palette_canvas.itemconfig(self.bg_image_id, image=self.palette_photo)

        # Поднимаем курсор наверх
        self.palette_canvas.tag_raise(self.cursor_id)
        self.palette_canvas.tag_raise(self.cursor_inner_id)

    def on_palette_click(self, event):
        self.update_from_palette(event.x, event.y)

    def on_palette_drag(self, event):
        self.update_from_palette(event.x, event.y)

    def update_from_palette(self, x, y):
        x = max(0, min(self.palette_width, x))
        y = max(0, min(self.palette_height, y))

        hue = x / self.palette_width
        lightness = 1.0 - (y / self.palette_height)
        saturation = self.vars['HLS']['S'].get() / 100.0

        if self.updating:
            return
        self.updating = True

        r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
        self.current_rgb = (int(r * 255), int(g * 255), int(b * 255))

        self.updating = False
        self.update_all_from_rgb()

    def update_cursor_from_vars(self):
        """Обновляет положение курсора исходя из текущих значений (вызывается в т.ч. при ресайзе окна)"""
        try:
            h = self.vars['HLS']['H'].get() / 360.0
            l = self.vars['HLS']['L'].get() / 100.0
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
            self.current_rgb = (int(color[0][0]), int(color[0][1]), int(color[0][2]))
            self.update_all_from_rgb()

    def on_rgb_change(self):
        if self.updating:
            return
        try:
            r = max(0, min(255, self.vars['RGB']['R'].get()))
            g = max(0, min(255, self.vars['RGB']['G'].get()))
            b = max(0, min(255, self.vars['RGB']['B'].get()))
            self.current_rgb = (r, g, b)
            self.update_ui(exclude='RGB')
        except tk.TclError:
            pass

    def on_cmyk_change(self):
        if self.updating:
            return
        try:
            c = max(0, min(100, self.vars['CMYK']['C'].get())) / 100.0
            m = max(0, min(100, self.vars['CMYK']['M'].get())) / 100.0
            y = max(0, min(100, self.vars['CMYK']['Y'].get())) / 100.0
            k = max(0, min(100, self.vars['CMYK']['K'].get())) / 100.0
            r = int(255 * (1 - c) * (1 - k))
            g = int(255 * (1 - m) * (1 - k))
            b = int(255 * (1 - y) * (1 - k))
            self.current_rgb = (r, g, b)
            self.update_ui(exclude='CMYK')
        except tk.TclError:
            pass

    def on_hls_change(self):
        if self.updating:
            return
        try:
            h = max(0, min(360, self.vars['HLS']['H'].get())) / 360.0
            l = max(0, min(100, self.vars['HLS']['L'].get())) / 100.0
            s = max(0, min(100, self.vars['HLS']['S'].get())) / 100.0
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            self.current_rgb = (int(r * 255), int(g * 255), int(b * 255))
            self.update_ui(exclude='HLS')
        except tk.TclError:
            pass

    def update_all_from_rgb(self):
        self.update_ui(exclude=None)

    def update_ui(self, exclude):
        self.updating = True
        r, g, b = self.current_rgb

        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        self.color_preview.config(bg=hex_color)

        if exclude != 'RGB':
            self.vars['RGB']['R'].set(r)
            self.vars['RGB']['G'].set(g)
            self.vars['RGB']['B'].set(b)

        if exclude != 'CMYK':
            r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
            k = 1 - max(r_norm, g_norm, b_norm)
            if k == 1.0:
                c = 0
                m = 0
                y = 0
            else:
                c = (1 - r_norm - k) / (1 - k)
                m = (1 - g_norm - k) / (1 - k)
                y = (1 - b_norm - k) / (1 - k)
            self.vars['CMYK']['C'].set(int(round(c * 100)))
            self.vars['CMYK']['M'].set(int(round(m * 100)))
            self.vars['CMYK']['Y'].set(int(round(y * 100)))
            self.vars['CMYK']['K'].set(int(round(k * 100)))

        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        if exclude != 'HLS':
            self.vars['HLS']['H'].set(int(round(h * 360)))
            self.vars['HLS']['L'].set(int(round(l * 100)))
            self.vars['HLS']['S'].set(int(round(s * 100)))

        self.generate_base_palette(s)
        self.update_cursor_position(h, l)
        self.updating = False


root = tk.Tk()
app = ColorApp(root)
root.mainloop()
