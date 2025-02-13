"""
Асинхронное главное приложение для кросс-постинга с продвинутыми функциями

Требует установки:
pip install apscheduler async-timeout
"""

import asyncio
import logging
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Set, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.interval import IntervalTrigger

from config import (
    SEARCH_KEYWORDS,
    RESULTS_COUNT,
    PROCESSED_VIDEOS_FILE,
    CHECK_INTERVAL_SECONDS,
    MAX_FILE_SIZE_MB,
    DELETE_LOCAL_COPY
)

# Импорт улучшенных модулей
from vk_parser import VKVideoParserAsync, VKParserError
from video_downloader import AsyncVideoDownloader, VideoDownloadError
from telegram_poster import AsyncTelegramPoster, TelegramPosterError

# Настройка логгера
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ApplicationState:
    """Класс для управления состоянием приложения"""
    
    def __init__(self):
        self.processed_videos: Set[str] = set()
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = True

    async def load_processed_videos(self) -> None:
        """Асинхронная загрузка обработанных видео"""
        try:
            path = Path(PROCESSED_VIDEOS_FILE)
            if await asyncio.to_thread(path.exists):
                async with asyncio.Lock():
                    content = await asyncio.to_thread(path.read_text, encoding='utf-8')
                    self.processed_videos = set(content.splitlines())
                logger.info(f"Loaded {len(self.processed_videos)} processed videos")
        except Exception as e:
            logger.error(f"Error loading processed videos: {e}")

    async def save_processed_video(self, video_id: str) -> None:
        """Асинхронное сохранение обработанного видео"""
        try:
            async with asyncio.Lock():
                with open(PROCESSED_VIDEOS_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"{video_id}\n")
                self.processed_videos.add(video_id)
        except Exception as e:
            logger.error(f"Error saving video ID {video_id}: {e}")

class Application:
    """Основной класс приложения"""
    
    def __init__(self):
        self.state = ApplicationState()
        self.vk_parser = VKVideoParserAsync()
        self.downloader = AsyncVideoDownloader()
        self.tg_poster = AsyncTelegramPoster()
        self._setup_scheduler()

    def _setup_scheduler(self) -> None:
        """Конфигурация планировщика задач"""
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
        }
        self.state.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            timezone="UTC"
        )

    async def startup(self) -> None:
        """Инициализация приложения"""
        await self.state.load_processed_videos()
        self._register_signals()
        
        # Первый запуск через 10 секунд после старта
        self.state.scheduler.add_job(
            self.process_videos,
            trigger=IntervalTrigger(
                seconds=CHECK_INTERVAL_SECONDS,
                start_date=datetime.now() + timedelta(seconds=10)
            ),
            max_instances=3
        )
        
        self.state.scheduler.start()
        logger.info("Application started")

    async def shutdown(self) -> None:
        """Корректное завершение работы"""
        logger.info("Shutting down application...")
        self.state.is_running = False
        
        if self.state.scheduler:
            await asyncio.to_thread(self.state.scheduler.shutdown)
        
        await self.downloader.cleanup()
        logger.info("Cleanup completed")

    def _register_signals(self) -> None:
        """Регистрация обработчиков сигналов"""
        loop = asyncio.get_running_loop()
        for signame in ('SIGINT', 'SIGTERM'):
            loop.add_signal_handler(
                getattr(signal, signame),
                lambda: asyncio.create_task(self.shutdown())
            )

    async def process_videos(self) -> None:
        """Основной рабочий процесс"""
        if not self.state.is_running:
            return

        logger.info("Starting video processing cycle")
        
        try:
            async with self.vk_parser, self.tg_poster:
                videos = await self.vk_parser.search_videos(
                    count=RESULTS_COUNT,
                    extended_metadata=True
                )
                
                for video in videos:
                    video_id = f"{video['owner_id']}_{video['id']}"
                    if video_id in self.state.processed_videos:
                        logger.debug(f"Skipping already processed video {video_id}")
                        continue
                    
                    await self._process_single_video(video, video_id)
                    
        except VKParserError as e:
            logger.error(f"VK processing error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    async def _process_single_video(self, video: dict, video_id: str) -> None:
        """Обработка одного видео"""
        try:
            # Скачивание видео
            downloaded_path = await self.downloader.download(
                url=video['url'],
                filename=f"video_{video_id}",
                quality='720p'
            )
            
            # Публикация в Telegram
            caption = self._generate_caption(video)
            await self.tg_poster.send_video(
                caption=caption,
                video_path=downloaded_path,
                stream_upload=True
            )
            
            # Обновление состояния
            await self.state.save_processed_video(video_id)
            logger.info(f"Successfully processed video {video_id}")

        except VideoDownloadError as e:
            logger.warning(f"Download failed for {video_id}: {e}")
            await self._handle_download_failure(video)
            
        except TelegramPosterError as e:
            logger.error(f"Telegram post failed for {video_id}: {e}")
            await self._handle_posting_failure(downloaded_path)

    def _generate_caption(self, video: dict) -> str:
        """Генерация подписи с форматированием"""
        title = video.get('title', 'Без названия').replace('*', '★')
        description = video.get('description', '').replace('*', '★')
        date = video['date'].strftime('%d.%m.%Y %H:%M')
        return (
            f"*{title}*\n\n"
            f"{description}\n\n"
            f"📅 {date} | 👀 {video.get('views', 0)}"
        )

    async def _handle_download_failure(self, video: dict) -> None:
        """Обработка ошибок загрузки"""
        try:
            caption = f"*Не удалось загрузить видео*\n{video['title']}\n{video['url']}"
            await self.tg_poster.send_text(caption)
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")

    async def _handle_posting_failure(self, video_path: Path) -> None:
        """Обработка ошибок публикации"""
        try:
            if video_path.exists():
                await self.downloader.cleanup()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

async def main():
    """Точка входа в приложение"""
    app = Application()
    await app.startup()
    
    while app.state.is_running:
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
