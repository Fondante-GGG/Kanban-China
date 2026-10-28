import re
import opencc
from typing import Dict, Optional
from deep_translator import MyMemoryTranslator, GoogleTranslator
from backend.application.interfaces.services import ITranslationService


class ResilientTranslationService(ITranslationService):
    def __init__(self):
        self._s2t = opencc.OpenCC('s2t')
        self._t2s = opencc.OpenCC('t2s')
        # In-memory LRU / translation cache
        self._cache: Dict[str, Dict[str, str]] = {}

    def detect_language(self, text: str) -> str:
        if not text or not text.strip():
            return "ru"

        # Check for Chinese CJK characters
        if re.search(r'[\u4e00-\u9fff]', text):
            return "zh"

        # Check for unique Kyrgyz Cyrillic characters
        if re.search(r'[ңөүҢӨҮ]', text):
            return "ky"

        # Standard Cyrillic default to Russian
        if re.search(r'[\u0400-\u04ff]', text):
            return "ru"

        return "ru"

    def convert_chinese(self, text: str, target_variant: str) -> str:
        if not text:
            return ""
        if target_variant in ("zh-Hant", "traditional"):
            return self._s2t.convert(text)
        return self._t2s.convert(text)

    def _translate_single(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text or not text.strip():
            return ""
        if source_lang == target_lang:
            return text

        cache_key = f"{source_lang}->{target_lang}:{text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Language code mappings for translators
        mymemory_lang_map = {
            "ru": "ru-RU",
            "zh": "zh-CN",
            "zh-CN": "zh-CN",
            "zh-TW": "zh-TW",
            "ky": "ky-KG",
            "en": "en-GB"
        }
        google_lang_map = {
            "ru": "ru",
            "zh": "zh-CN",
            "zh-CN": "zh-CN",
            "zh-TW": "zh-TW",
            "ky": "ky",
            "en": "en"
        }

        # Try MyMemory Translator first
        try:
            src = mymemory_lang_map.get(source_lang, source_lang)
            tgt = mymemory_lang_map.get(target_lang, target_lang)
            translator = MyMemoryTranslator(source=src, target=tgt)
            res = translator.translate(text)
            if res and not res.startswith("MYMEMORY WARNING"):
                self._cache[cache_key] = res
                return res
        except Exception:
            pass

        # Try Google Translator fallback
        try:
            src = google_lang_map.get(source_lang, source_lang)
            tgt = google_lang_map.get(target_lang, target_lang)
            translator = GoogleTranslator(source=src, target=tgt)
            res = translator.translate(text)
            if res:
                self._cache[cache_key] = res
                return res
        except Exception:
            pass

        # If offline or service unavailable, return text gracefully
        return text

    def translate_multilingual(self, text: str, source_lang: Optional[str] = None) -> Dict[str, str]:
        if not text or not text.strip():
            return {"ru": "", "zh": "", "ky": ""}

        detected = source_lang or self.detect_language(text)
        if detected not in ("ru", "zh", "ky"):
            detected = "ru"

        results = {
            "ru": text if detected == "ru" else "",
            "zh": text if detected == "zh" else "",
            "ky": text if detected == "ky" else "",
        }

        target_langs = [l for l in ["ru", "zh", "ky"] if l != detected]
        for t_lang in target_langs:
            try:
                translated = self._translate_single(text, detected, t_lang)
                results[t_lang] = translated or text
            except Exception:
                results[t_lang] = text

        # Provide explicit Chinese Traditional and Simplified variants via OpenCC
        zh_text = results.get("zh", "")
        if zh_text:
            results["zh-Hans"] = self._t2s.convert(zh_text)
            results["zh-Hant"] = self._s2t.convert(zh_text)
        else:
            results["zh-Hans"] = ""
            results["zh-Hant"] = ""

        return results
