"""
Асинхронный загрузчик видео с поддержкой прогресса, ограничениями и продвинутыми настройками

Требует установки: 
pip install yt-dlp aiofiles tqdm
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from tqdm import tqdm
import yt_dlp
from yt_dlp.utils import DownloadError

from config import (
    DOWNLOAD_PATH,
    MAX_FILE_SIZE_MB,
    DELETE_LOCAL_COPY,
    PROXY_SETTINGS,
    TELEGRAM_API_TIMEOUT
)

logger = logging.getLogger(__name__)

class VideoDownloadError(Exception):
    """Базовое исключение для ошибок загрузки видео"""
    pass

class VideoSizeExceededError(VideoDownloadError):
    """Исключение при превышении максимального размера файла"""
    pass

class AsyncVideoDownloader:
    """Асинхронный загрузчик видео с поддержкой прогресса и ограничений"""
    
    def __init__(self):
        self.progress_bars: Dict[str, tqdm] = {}
        self.download_path = Path(DOWNLOAD_PATH)
        self._prepare_directory()

    def _prepare_directory(self) -> None:
        """Создает директорию для загрузок и проверяет права"""
        try:
            self.download_path.mkdir(parents=True, exist_ok=True)
            if not os.access(self.download_path, os.W_OK):
                raise PermissionError(f"No write access to {self.download_path}")
        except Exception as e:
            logger.error(f"Directory error: {e}")
            raise

    async def download(
        self,
        url: str,
        filename: str,
        quality: str = 'best',
        codec: Optional[str] = None
    ) -> Optional[Path]:
        """
        Асинхронная загрузка видео с обработкой прогресса
        
        :param url: URL видео для загрузки
        :param filename: Имя выходного файла (без расширения)
        :param quality: Качество видео (best, 1080p, 720p и т.д.)
        :param codec: Предпочитаемый кодек (h264, vp9 и т.д.)
        :return: Path к скачанному файлу или None при ошибке
        """
        loop = asyncio.get_running_loop()
        final_path = None
        
        try:
            ydl_opts = self._build_ydl_opts(filename, quality, codec)
            
            with tqdm(
                desc=f"Downloading {filename}",
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                leave=False
            ) as pbar:
                self.progress_bars[url] = pbar
                
                try:
                    final_path = await loop.run_in_executor(
                        None,
                        self._sync_download,
                        url,
                        ydl_opts
                    )
                finally:
                    del self.progress_bars[url]

            if final_path and (final_path.stat().st_size > MAX_FILE_SIZE_MB * 1024 * 1024):
                raise VideoSizeExceededError(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit")

            return final_path

        except DownloadError as e:
            logger.error(f"Download error: {e}")
            if final_path and final_path.exists():
                final_path.unlink()
            raise VideoDownloadError(f"YT-DLP error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise VideoDownloadError(f"Download failed: {e}") from e

    def _build_ydl_opts(self, filename: str, quality: str, codec: Optional[str]) -> Dict[str, Any]:
        """Создает конфигурацию для yt-dlp"""
        return {
            'outtmpl': str(self.download_path / f"{filename}.%(ext)s"),
            'format': self._build_format_string(quality, codec),
            'proxy': PROXY_SETTINGS.get('https') if PROXY_SETTINGS else None,
            'socket_timeout': TELEGRAM_API_TIMEOUT,
            'noprogress': True,
            'progress_hooks': [self._progress_hook],
            'merge_output_format': 'mp4',
            'writethumbnail': True,
            'postprocessors': [{
                'key': 'FFmpegMetadata'
            }],
            'retries': 3,
            'fragment_retries': 5,
            'skip_unavailable_fragments': True,
        }

    def _progress_hook(self, d: Dict) -> None:
        """Обработчик прогресса загрузки"""
        if pbar := self.progress_bars.get(d['info_dict']['url']):
            if d['status'] == 'downloading':
                pbar.total = d.get('total_bytes') or d.get('total_bytes_estimate')
                pbar.update(d['downloaded_bytes'] - pbar.n)

    @staticmethod
    def _build_format_string(quality: str, codec: Optional[str]) -> str:
        """Генерирует строку формата для yt-dlp"""
        format_str = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
        if codec:
            format_str += f"[vcodec~='^{codec}']"
        return format_str

    def _sync_download(self, url: str, ydl_opts: Dict) -> Path:
        """Синхронная обертка для yt-dlp"""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return Path(ydl.prepare_filename(info))

    async def cleanup(self) -> None:
        """Очистка временных файлов"""
        if DELETE_LOCAL_COPY:
            for file in self.download_path.glob('*'):
                try:
                    await asyncio.to_thread(file.unlink)
                except Exception as e:
                    logger.warning(f"Cleanup error: {e}")

async def main():
    """Пример использования"""
    downloader = AsyncVideoDownloader()
    try:
        video = await downloader.download(
            url='https://youtu.be/dQw4w9WgXcQ',
            filename='example_video',
            quality='720p',
            codec='h264'
        )
        if video:
            print(f"Successfully downloaded: {video}")
    except VideoDownloadError as e:
        logger.error(f"Download failed: {e}")
    finally:
        await downloader.cleanup()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main()