from pydantic import BaseModel, Field, field_validator
from datetime import UTC, datetime

class Quote(BaseModel):
    """Модель одной цитаты."""
    text: str = Field(..., description="Текст цитаты")
    author: str = Field(..., description="Автор цитаты")
    tags: list[str] = Field(default_factory=list, description="Теги цитаты")

class ScrapingResult(BaseModel):
    """Результат скрапинга с метаданными."""
    quotes: list[Quote] = Field(default_factory=list, description="Список цитат")
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Время скрапинга")
    total_count: int = Field(0, description="Количество собранных цитат")

    def add_quote(self, quote: Quote) -> None:
        """Добавить цитату и обновить счётчик."""
        self.quotes.append(quote)
        self.total_count = len(self.quotes)

    def to_dict(self) -> dict:
        """Сериализация в словарь для JSON."""
        return self.model_dump(mode='json')


class JobCreateRequest(BaseModel):
    """Запрос на создание задания скрапинга."""
    url: str = Field(..., description="URL страницы для скрапинга")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """URL должен начинаться с http:// или https://."""
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return value


class JobResponse(BaseModel):
    """Ответ после постановки задания в очередь."""
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    """Текущий статус задания."""
    id: str
    status: str
    error: str | None = None
    created_at: str
    updated_at: str