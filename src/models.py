# src/models.py
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class Quote(BaseModel):
    """Модель одной цитаты."""
    text: str = Field(..., description="Текст цитаты")
    author: str = Field(..., description="Автор цитаты")
    tags: List[str] = Field(default_factory=list, description="Теги цитаты")

class ScrapingResult(BaseModel):
    """Результат скрапинга с метаданными."""
    quotes: List[Quote] = Field(default_factory=list, description="Список цитат")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="Время скрапинга")
    total_count: int = Field(0, description="Количество собранных цитат")

    def add_quote(self, quote: Quote) -> None:
        """Добавить цитату и обновить счётчик."""
        self.quotes.append(quote)
        self.total_count = len(self.quotes)

    def to_dict(self) -> dict:
        """Сериализация в словарь для JSON."""
        return self.model_dump(mode='json')