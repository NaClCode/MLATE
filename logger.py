import logging
import sys
import os

class MLATELogger:
    """Logger supporting English (default), Chinese, and bilingual output."""
    
    def __init__(self):
        self._logger = logging.getLogger("mlate")
        self._logger.setLevel(logging.INFO)
        
        # Default output to stdout
        self._handler = logging.StreamHandler(sys.stdout)
        self._formatter = logging.Formatter("%(message)s")
        self._handler.setFormatter(self._formatter)
        self._logger.addHandler(self._handler)
        
        # Language settings: 'cn', 'en', 'both'
        # Priority: Env var MLATE_LANG > Default (en)
        self.lang = os.environ.get("MLATE_LANG", "en").lower()

    def set_level(self, level):
        """Set logging level."""
        self._logger.setLevel(level)

    def set_lang(self, lang: str):
        """Set output language: 'cn', 'en', 'both'"""
        if lang in ["cn", "en", "both"]:
            self.lang = lang

    def _format(self, cn: str, en: str = None) -> str:
        """Format message based on language settings."""
        if en is None:
            return cn
        
        if self.lang == "cn":
            return cn
        elif self.lang == "en":
            return en
        else:
            # Bilingual mode
            return f"{cn} | {en}"

    def info(self, cn: str, en: str = None):
        """Log info message."""
        self._logger.info(self._format(cn, en))

    def error(self, cn: str, en: str = None):
        """Log error message."""
        self._logger.error(self._format(cn, en))

    def warning(self, cn: str, en: str = None):
        """Log warning message."""
        self._logger.warning(self._format(cn, en))

    def success(self, cn: str, en: str = None):
        """Log success message with a checkmark."""
        self._logger.info(f"✓ {self._format(cn, en)}")

    def section(self, cn: str, en: str = None):
        """Log section header."""
        msg = self._format(cn, en)
        self._logger.info(f"\n── {msg} ──")

    def separator(self):
        """Log separator line."""
        self._logger.info("-" * 50)

# 全局单例
logger = MLATELogger()
