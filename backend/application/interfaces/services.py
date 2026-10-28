from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.domain.entities import User


class ITokenService(ABC):
    @abstractmethod
    def generate_token(self, user: User) -> str:
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Dict[str, Any]:
        pass


class ITranslationService(ABC):
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Detects whether text is 'ru', 'zh', or 'ky'."""
        pass

    @abstractmethod
    def translate_multilingual(self, text: str, source_lang: Optional[str] = None) -> Dict[str, str]:
        """Returns dict with keys: 'ru', 'zh', 'ky' containing translations for all three languages."""
        pass

    @abstractmethod
    def convert_chinese(self, text: str, target_variant: str) -> str:
        """Converts Chinese between Simplified ('zh-Hans') and Traditional ('zh-Hant')."""
        pass


class IReportService(ABC):
    @abstractmethod
    def get_analytics_data(self, uow: Any, period: str, start_date: Optional[str], end_date: Optional[str], department_id: Optional[int]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def export_excel(self, data: Dict[str, Any]) -> bytes:
        pass

    @abstractmethod
    def export_word(self, data: Dict[str, Any]) -> bytes:
        pass

    @abstractmethod
    def export_pdf(self, data: Dict[str, Any]) -> bytes:
        pass
