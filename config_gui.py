import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext

class PlaceholderEntry(tk.Entry):
    """
    Кастомное поле ввода с поддержкой placeholder.
    При фокусе placeholder удаляется, а при потере фокуса — возвращается,
    если поле пустое.
    """
    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey', **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)
        self._add_placeholder()
    
    def _add_placeholder(self, event=None):
        if not self.get():
            self.insert(0, self.placeholder)
            self.config(fg=self.placeholder_color)
    
    def _clear_placeholder(self, event=None):
        if self.get() == self.placeholder and self['fg'] == self.placeholder_color:
            self.delete(0, tk.END)
            self.config(fg=self.default_fg_color)
    
    def get_value(self):
        """
        Возвращает введённое значение, исключая placeholder.
        """
        val = self.get()
        if val == self.placeholder and self['fg'] == self.placeholder_color:
            return ""
        return val

class ConfigApp:
    def __init__(self, master):
        self.master = master
        master.title("Настройка конфигурации проекта")
        master.columnconfigure(1, weight=1)  # Второй столбец расширяется
        
        row = 0
        
        # VK API Token
        tk.Label(master, text="VK API Token:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.entry_vk_token = PlaceholderEntry(master, placeholder="Введите ваш VK API токен", width=50)
        self.entry_vk_token.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Telegram Bot Token
        tk.Label(master, text="Telegram Bot Token:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.entry_telegram_token = PlaceholderEntry(master, placeholder="Введите токен вашего Telegram бота", width=50)
        self.entry_telegram_token.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Список каналов (необязательно)
        tk.Label(master, text="Список каналов (через запятую):").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.entry_channels = PlaceholderEntry(
            master,
            placeholder="Оставьте пустым, если каналы нужно найти по ключевым словам",
            width=50
        )
        self.entry_channels.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Ключевые слова для поиска
        tk.Label(master, text="Ключевые слова для поиска:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.entry_search_keywords = PlaceholderEntry(master, placeholder="Введите ключевые слова через запятую", width=50)
        self.entry_search_keywords.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Количество видео
        tk.Label(master, text="Количество видео:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.entry_results_count = PlaceholderEntry(master, placeholder="Введите целое число, например: 5", width=50)
        self.entry_results_count.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Папка для скачивания видео с кнопкой «Обзор...»
        tk.Label(master, text="Папка для скачивания видео:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.entry_download_path = PlaceholderEntry(
            master,
            placeholder="Укажите полный путь к папке, например: C:\\Videos",
            width=50
        )
        self.entry_download_path.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        self.browse_button = tk.Button(master, text="Обзор...", command=self.browse_folder)
        self.browse_button.grid(row=row, column=2, padx=5, pady=5)
        row += 1
        
        # Интервал проверки
        tk.Label(master, text="Интервал проверки (сек):").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.entry_check_interval = PlaceholderEntry(master, placeholder="Введите интервал в секундах, например: 60", width=50)
        self.entry_check_interval.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Файл для обработанных видео
        tk.Label(master, text="Файл для обработанных видео:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.entry_processed_videos_file = PlaceholderEntry(master, placeholder="Например: processed.txt", width=50)
        self.entry_processed_videos_file.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        row += 1
        
        # Кнопки «Сохранить» и «Инструкция»
        self.save_button = tk.Button(master, text="Сохранить", command=self.save_config)
        self.save_button.grid(row=row, column=1, padx=5, pady=10, sticky="e")
        
        self.instruction_button = tk.Button(master, text="Инструкция", command=self.show_instructions)
        self.instruction_button.grid(row=row, column=0, padx=5, pady=10, sticky="w")
    
    def browse_folder(self):
        """Открывает диалог выбора папки и заполняет поле 'Папка для скачивания видео'."""
        folder = filedialog.askdirectory()
        if folder:
            self.entry_download_path.delete(0, tk.END)
            self.entry_download_path.insert(0, folder)
            self.entry_download_path.config(fg='black')
    
    def save_config(self):
        """Собирает данные, выполняет валидацию и сохраняет их в файл config.py."""
        vk_token = self.entry_vk_token.get_value()
        telegram_token = self.entry_telegram_token.get_value()
        channels_str = self.entry_channels.get_value()
        search_keywords = self.entry_search_keywords.get_value()
        results_count = self.entry_results_count.get_value()
        download_path = self.entry_download_path.get_value()
        check_interval = self.entry_check_interval.get_value()
        processed_videos_file = self.entry_processed_videos_file.get_value()
        
        # Проверка обязательных полей (список каналов — необязательный)
        if not (vk_token and telegram_token and search_keywords and results_count and download_path and check_interval and processed_videos_file):
            messagebox.showerror(
                "Ошибка",
                "Пожалуйста, заполните все обязательные поля.\nЕсли у вас нет списка каналов, оставьте поле пустым."
            )
            return
        
        try:
            results_count_int = int(results_count)
            check_interval_int = int(check_interval)
        except ValueError:
            messagebox.showerror("Ошибка", "Поля 'Количество видео' и 'Интервал проверки' должны быть целыми числами.")
            return
        
        # Если список каналов пуст, оставляем его пустым — каналы будут искаться по ключевым словам
        channels_list = [ch.strip() for ch in channels_str.split(',') if ch.strip()] if channels_str else []
        
        config_content = f'''# Автоматически сгенерированный файл конфигурации
VK_TOKEN = "{vk_token}"
TELEGRAM_TOKEN = "{telegram_token}"
CHANNEL_IDS = {channels_list}  # Если список пуст, каналы будут найдены по ключевым словам
SEARCH_KEYWORDS = "{search_keywords}"
RESULTS_COUNT = {results_count_int}
DOWNLOAD_PATH = "{download_path}"
CHECK_INTERVAL_SECONDS = {check_interval_int}
PROCESSED_VIDEOS_FILE = "{processed_videos_file}"
'''
        try:
            with open("config.py", "w", encoding="utf-8") as f:
                f.write(config_content)
            messagebox.showinfo("Успех", "Конфигурация успешно сохранена в config.py.")
            self.master.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить конфигурацию: {e}")
    
    def show_instructions(self):
        """
        Открывает новое окно с подробной инструкцией, включая адреса для получения API-токенов
        и объяснением, как вводить данные.
        """
        instructions_text = (
            "Инструкция по настройке API и данных:\n\n"
            "1. VK API Token:\n"
            "   - Перейдите на https://vk.com/dev, создайте приложение и получите токен доступа.\n\n"
            "2. Telegram Bot Token:\n"
            "   - Создайте нового бота через BotFather в Telegram. Подробности: https://core.telegram.org/bots#3-how-do-i-create-a-bot\n\n"
            "3. Список каналов:\n"
            "   - Введите идентификаторы или имена каналов через запятую, если они известны.\n"
            "   - Если поле оставлено пустым, каналы будут найдены по заданным ключевым словам.\n\n"
            "4. Ключевые слова для поиска:\n"
            "   - Укажите ключевые слова для поиска видео в VK, разделённые запятыми.\n\n"
            "5. Количество видео:\n"
            "   - Укажите целое число, определяющее, сколько видео обрабатывать за один раз.\n\n"
            "6. Папка для скачивания видео:\n"
            "   - Укажите полный путь к директории, куда будут сохраняться видео.\n"
            "   - Можно воспользоваться кнопкой 'Обзор...'.\n\n"
            "7. Интервал проверки (сек):\n"
            "   - Укажите интервал в секундах для проверки появления новых видео.\n\n"
            "8. Файл для обработанных видео:\n"
            "   - Укажите имя файла, в котором будет сохраняться информация о уже обработанных видео.\n\n"
            "Дополнительные ресурсы:\n"
            "   - VK API документация: https://vk.com/dev\n"
            "   - Telegram Bot API: https://core.telegram.org/bots/api\n"
        )
        
        instr_window = tk.Toplevel(self.master)
        instr_window.title("Инструкция по настройке")
        instr_window.geometry("600x400")
        
        text_widget = scrolledtext.ScrolledText(instr_window, wrap="word", padx=10, pady=10)
        text_widget.insert(tk.END, instructions_text)
        text_widget.config(state="disabled")
        text_widget.pack(expand=True, fill="both")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigApp(root)
    root.mainloop()
