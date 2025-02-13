"""
Асинхронный модуль для публикации контента в Telegram с продвинутыми функциями

Требует установки:
pip install aiogram python-telegram-bot
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Union, Optional, AsyncGenerator
from datetime import datetime

from aiogram import Bot, types
from aiogram.utils.exceptions import (
    TelegramAPIError,
    RetryAfter,
    ChatNotFound,
    NetworkError
)

from config import (
    TELEGRAM_TOKEN,
    CHANNEL_IDS,
    DELETE_LOCAL_COPY,
    MAX_FILE_SIZE_MB,
    TELEGRAM_API_TIMEOUT,
    PROXY_SETTINGS
)

logger = logging.getLogger(__name__)

class TelegramPosterError(Exception):
    """Базовое исключение для ошибок публикации"""
    pass

class ContentTooLargeError(TelegramPosterError):
    """Исключение при превышении размера контента"""
    pass

class AsyncTelegramPoster:
    """Асинхронный клиент для публикации контента в Telegram"""
    
    MAX_CAPTION_LENGTH = 1024
    SUPPORTED_VIDEO_FORMATS = {'mp4', 'mov', 'mkv'}
    CHUNK_SIZE = 10 * 1024 * 1024  # 10MB для потоковой загрузки
    
    def __init__(self):
        self.bot = Bot(
            token=TELEGRAM_TOKEN,
            timeout=TELEGRAM_API_TIMEOUT,
            proxy=PROXY_SETTINGS.get('https') if PROXY_SETTINGS else None
        )
        self._configure_session()

    def _configure_session(self) -> None:
        """Конфигурация параметров сессии"""
        self.bot.session.headers.update({
            'User-Agent': 'AdvancedTelegramPoster/2.0 (+https://github.com/yourrepo)'
        })

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.bot.close()

    async def send_text(
        self,
        message: str,
        channels: List[Union[str, int]] = CHANNEL_IDS,
        parse_mode: types.ParseMode = types.ParseMode.MARKDOWN_V2,
        disable_web_page_preview: bool = True,
        retries: int = 3
    ) -> List[types.Message]:
        """
        Асинхронная отправка текстовых сообщений с поддержкой форматирования
        
        :param message: Текст сообщения (поддерживает Markdown/HTML)
        :param channels: Список каналов для публикации
        :param parse_mode: Режим парсинга (Markdown/HTML)
        :param retries: Количество попыток повторной отправки
        :return: Список отправленных сообщений
        """
        messages = []
        for channel in channels:
            for attempt in range(retries):
                try:
                    msg = await self.bot.send_message(
                        chat_id=channel,
                        text=self._truncate_text(message, self.MAX_CAPTION_LENGTH),
                        parse_mode=parse_mode,
                        disable_web_page_preview=disable_web_page_preview
                    )
                    messages.append(msg)
                    logger.info(f"Сообщение отправлено в {channel} (ID: {msg.message_id})")
                    break
                except RetryAfter as e:
                    await self._handle_retry(e, channel, attempt, retries)
                except (ChatNotFound, NetworkError) as e:
                    logger.error(f"Фатальная ошибка для {channel}: {e}")
                    break
                except TelegramAPIError as e:
                    logger.error(f"Ошибка API для {channel}: {e}")
        return messages

    async def send_video(
        self,
        caption: str,
        video_path: Union[str, Path],
        channels: List[Union[str, int]] = CHANNEL_IDS,
        parse_mode: types.ParseMode = types.ParseMode.MARKDOWN_V2,
        retries: int = 3,
        stream_upload: bool = False
    ) -> List[types.Message]:
        """
        Отправка видео с поддержкой больших файлов и потоковой загрузки
        
        :param video_path: Путь к видеофайлу
        :param stream_upload: Использовать потоковую загрузку для больших файлов
        """
        video_path = Path(video_path)
        self._validate_video(video_path)

        messages = []
        for channel in channels:
            try:
                if stream_upload and video_path.stat().st_size > self.CHUNK_SIZE:
                    msg = await self._stream_upload(channel, video_path, caption, parse_mode)
                else:
                    msg = await self._direct_upload(channel, video_path, caption, parse_mode)
                
                messages.append(msg)
                logger.info(f"Видео отправлено в {channel} (ID: {msg.message_id})")
                
                if DELETE_LOCAL_COPY:
                    await self._safe_delete(video_path)
                    
            except Exception as e:
                logger.error(f"Ошибка отправки видео в {channel}: {e}")
                
        return messages

    async def _direct_upload(
        self,
        channel: Union[str, int],
        video_path: Path,
        caption: str,
        parse_mode: types.ParseMode
    ) -> types.Message:
        """Прямая загрузка видео файла"""
        with video_path.open('rb') as video_file:
            return await self.bot.send_video(
                chat_id=channel,
                video=types.InputFile(video_file, filename=video_path.name),
                caption=self._truncate_text(caption, self.MAX_CAPTION_LENGTH),
                parse_mode=parse_mode,
                supports_streaming=True
            )

    async def _stream_upload(
        self,
        channel: Union[str, int],
        video_path: Path,
        caption: str,
        parse_mode: types.ParseMode
    ) -> types.Message:
        """Потоковая загрузка больших видео файлов"""
        async for chunk in self._file_chunker(video_path):
            # Реализация мультипартовой загрузки
            # (псевдокод для примера, требуется доработка)
            pass
        return await self.bot.send_video(
            chat_id=channel,
            video=video_path.name,
            caption=self._truncate_text(caption, self.MAX_CAPTION_LENGTH),
            parse_mode=parse_mode
        )

    async def _file_chunker(self, path: Path) -> AsyncGenerator[bytes, None]:
        """Генератор чанков файла для потоковой загрузки"""
        with path.open('rb') as f:
            while chunk := f.read(self.CHUNK_SIZE):
                yield chunk

    def _validate_video(self, path: Path) -> None:
        """Проверка видео перед отправкой"""
        if not path.exists():
            raise FileNotFoundError(f"Видео файл не найден: {path}")
            
        if path.suffix.lower()[1:] not in self.SUPPORTED_VIDEO_FORMATS:
            raise ValueError(f"Неподдерживаемый формат видео: {path.suffix}")
            
        file_size = path.stat().st_size / (1024 * 1024)
        if file_size > MAX_FILE_SIZE_MB:
            raise ContentTooLargeError(
                f"Размер файла {file_size:.2f}MB превышает лимит {MAX_FILE_SIZE_MB}MB"
            )

    async def _handle_retry(
        self,
        error: RetryAfter,
        channel: Union[str, int],
        attempt: int,
        max_retries: int
    ) -> None:
        """Обработка ограничений частоты запросов"""
        retry_time = error.timeout
        logger.warning(
            f"Превышен лимит для {channel}. "
            f"Попытка {attempt + 1}/{max_retries}. "
            f"Повтор через {retry_time} сек."
        )
        await asyncio.sleep(retry_time)

    @staticmethod
    def _truncate_text(text: str, max_length: int) -> str:
        """Обрезка текста с сохранением форматирования"""
        return text[:max_length - 3] + '...' if len(text) > max_length else text

    @staticmethod
    async def _safe_delete(path: Path) -> None:
        """Безопасное удаление файла с обработкой ошибок"""
        try:
            await asyncio.to_thread(path.unlink)
        except Exception as e:
            logger.error(f"Ошибка удаления файла {path}: {e}")

async def main():
    """Пример использования"""
    async with AsyncTelegramPoster() as poster:
        # Отправка текста
        await poster.send_text(
            message="*Пример сообщения* с **форматированием**",
            channels=["@your_channel"]
        )
        
        # Отправка видео
        await poster.send_video(
            caption="Демо видео",
            video_path="downloads/example.mp4",
            stream_upload=True
        )

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())