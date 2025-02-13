"""
Асинхронный модуль для работы с VK API с улучшенной производительностью и кешированием

Требует установки: 
pip install aiohttp cachetools
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from cachetools import TTLCache
import aiohttp

from config import (
    VK_TOKEN,
    RESULTS_COUNT,
    VK_API_VERSION,
    SEARCH_KEYWORDS,
    PROXY_SETTINGS
)

logger = logging.getLogger(__name__)

class VKParserError(Exception):
    """Базовое исключение для ошибок парсера VK"""
    pass

class VKVideoParserAsync:
    """Асинхронный парсер видео с кешированием и продвинутой обработкой"""
    
    API_URL = "https://api.vk.com/method/video.search"
    MAX_RESULTS = 200
    CACHE_TTL = 300  # 5 минут кеширования
    REQUEST_TIMEOUT = 15
    
    def __init__(self):
        self.cache = TTLCache(maxsize=100, ttl=self.CACHE_TTL)
        self.session = None
        self.proxy = PROXY_SETTINGS if PROXY_SETTINGS else None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self._get_headers(),
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
        )
        return self
        
    async def __aexit__(self, *exc):
        await self.session.close()
        
    def _get_headers(self) -> Dict:
        return {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) VKParser/1.0",
            "Authorization": f"Bearer {VK_TOKEN}"
        }
    
    async def search_videos(
        self,
        query: str = SEARCH_KEYWORDS,
        count: int = RESULTS_COUNT,
        sort: int = 2,
        filters: Optional[List[str]] = None,
        extended_metadata: bool = True
    ) -> List[Dict]:
        """
        Асинхронный поиск видео с кешированием и расширенными метаданными
        
        :param extended_metadata: Получать дополнительные метаданные
        """
        cache_key = self._generate_cache_key(query, count, sort, filters)
        
        if cache_key in self.cache:
            logger.debug("Возвращаем результаты из кеша")
            return self.cache[cache_key]
            
        try:
            params = self._build_request_params(query, count, sort, filters)
            
            start_time = datetime.now()
            async with self.session.get(
                self.API_URL,
                params=params,
                proxy=self.proxy
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
            logger.info(f"Запрос выполнен за {(datetime.now() - start_time).total_seconds():.2f}s")
            
            processed = self._process_response(data, extended_metadata)
            self.cache[cache_key] = processed
            return processed
            
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка соединения: {e}")
            raise VKParserError(f"Network error: {e}") from e
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}")
            raise VKParserError(f"Request failed: {e}") from e

    def _build_request_params(self, query, count, sort, filters) -> Dict:
        """Сбор параметров запроса с валидацией"""
        count = max(1, min(count, self.MAX_RESULTS))
        return {
            "q": query,
            "count": count,
            "sort": sort,
            "filters": ','.join(filters) if filters else None,
            "extended": 1,
            "access_token": VK_TOKEN,
            "v": VK_API_VERSION
        }
    
    def _generate_cache_key(self, *args) -> Tuple:
        """Генерация ключа кеша на основе параметров"""
        return tuple(args) + (datetime.now().minute // (self.CACHE_TTL // 60),)

    def _process_response(self, data: Dict, extended_metadata: bool) -> List[Dict]:
        """Обработка и обогащение данных ответа"""
        if 'error' in data:
            error_msg = data['error'].get('error_msg', 'Unknown VK API error')
            logger.error(f"VK API Error: {error_msg}")
            raise VKParserError(error_msg)
            
        items = data.get('response', {}).get('items', [])
        
        if not items:
            return []
            
        return [self._enrich_video_data(video, extended_metadata) for video in items]
    
    def _enrich_video_data(self, video: Dict, extended: bool) -> Dict:
        """Добавление дополнительных метаданных к видео"""
        result = {
            'id': video.get('id'),
            'owner_id': video.get('owner_id'),
            'title': video.get('title'),
            'duration': video.get('duration'),
            'url': self.get_video_url(video),
            'views': video.get('views')
        }
        
        if extended:
            result.update({
                'preview': video.get('image'),
                'date': datetime.fromtimestamp(video.get('date', 0)),
                'player_url': video.get('player'),
                'description': video.get('description')
            })
            
        return result

    @staticmethod
    def get_video_url(video: Dict) -> str:
        """Генерация URL видео с проверкой обязательных полей"""
        required_fields = {'owner_id', 'id'}
        if not required_fields.issubset(video.keys()):
            raise VKParserError("Некорректный объект видео")
            
        return f"https://vk.com/video{video['owner_id']}_{video['id']}"

async def main():
    """Пример использования с контекстным менеджером"""
    try:
        async with VKVideoParserAsync() as parser:
            videos = await parser.search_videos(count=3, extended_metadata=True)
            for video in videos:
                print(f"[{video['date']}] {video['title']}")
                print(f"Views: {video['views']} | URL: {video['url']}\n")
                
    except VKParserError as e:
        logger.error(f"Ошибка: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
