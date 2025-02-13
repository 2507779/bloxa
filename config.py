# -*- coding: utf-8 -*-
"""
Конфигурация бота для кросс-постинга видео из VK в Telegram

Все настройки должны быть заполнены перед запуском бота.
Для работы требуется Python 3.8+.
"""

from typing import List, Union

# =====================
# VK API Configuration
# =====================

# VK API токен (получить можно в настройках приложения VK)
# Пример: "vk1.a.1a2b3c4d..."
VK_TOKEN: str = "YOUR_VK_API_TOKEN_HERE"

# Параметры поиска видео в VK
SEARCH_KEYWORDS: str = "python разработка"  # Поисковый запрос
RESULTS_COUNT: int = 5  # Количество результатов (макс. 200 для базового API)
PLATFORM: str = "youtube"  # Платформа для поиска (youtube/vimeo/etc)

# ========================
# Telegram Configuration
# ========================

# Токен бота Telegram (получить через @BotFather)
# Пример: "1234567890:ABCdefGHIJKLmnopQRSTuvwxyz"
TELEGRAM_TOKEN: str = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

# Целевые каналы/чаты (ID или username с @)
# Пример: ["@my_channel", -100123456789]
CHANNEL_IDS: List[Union[str, int]] = [
    '@your_channel1',
    '@your_channel2'
]

# =====================
# System Configuration
# =====================

# Настройки хранения данных
DOWNLOAD_PATH: str = "downloads"  # Папка для временного хранения видео
PROCESSED_VIDEOS_FILE: str = "processed_videos.txt"  # Лог обработанных видео

# Параметры работы бота
CHECK_INTERVAL_SECONDS: int = 600  # Интервал проверки (10-3600 сек)
MAX_FILE_SIZE_MB: int = 50  # Максимальный размер видео для загрузки (MB)
DELETE_LOCAL_COPY: bool = True  # Удалять ли скачанные видео после постинга

# ====================
# Advanced Settings
# ====================
# (Не менять без необходимости)

# API версии и лимиты
VK_API_VERSION: str = "5.199"
VK_API_URL: str = "https://api.vk.com/method/video.get"
TELEGRAM_API_TIMEOUT: int = 30  # Таймаут запросов к Telegram API

# Настройки прокси (при необходимости)
# PROXY_SETTINGS = {
#     "http": "http://user:pass@10.10.1.10:3128",
#     "https": "http://user:pass@10.10.1.10:1080",
# }