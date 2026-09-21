"""Enumerations and standardized codes for WeatherGPT contracts."""

from enum import Enum


class BrainType(str, Enum):
    """Supported Domain Brains and routing modes."""
    AUTO = "auto"
    GENERAL = "general"
    FARMER = "farmer"
    RESEARCHER = "researcher"
    ANALYST = "analyst"


class SupportedLanguage(str, Enum):
    """Supported Indian languages and ISO 639-1 codes."""
    ENGLISH = "en"
    HINDI = "hi"
    MARATHI = "mr"
    BENGALI = "bn"
    TAMIL = "ta"
    TELUGU = "te"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"


class RequestedOutputFormat(str, Enum):
    """Supported presentation and data export formats."""
    TEXT = "text"
    WEATHER_CARD = "weather_card"
    RECOMMENDATION = "recommendation"
    CHART = "chart"
    MAP = "map"
    TABLE = "table"
    DASHBOARD = "dashboard"
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"


class WarningLevel(str, Enum):
    """Official IMD warning color levels."""
    GREEN = "Green"
    YELLOW = "Yellow"
    ORANGE = "Orange"
    RED = "Red"


class AdvisoryAction(str, Enum):
    """Agronomic decision advisory actions."""
    IRRIGATE = "IRRIGATE"
    POSTPONE = "POSTPONE"
    POSTPONE_IRRIGATION = "POSTPONE_IRRIGATION"
    WITHHOLD = "WITHHOLD"
    SUITABLE = "SUITABLE"
    UNSUITABLE = "UNSUITABLE"
    MONITOR = "MONITOR"


class TemporalType(str, Enum):
    """Temporal classification for normalized time windows."""
    CURRENT = "current"
    RELATIVE_DAY = "relative_day"
    HOURLY_WINDOW = "hourly_window"
    MULTI_DAY_RANGE = "multi_day_range"
    HISTORICAL_PERIOD = "historical_period"
    SPECIFIC_DATE = "specific_date"


class LocationSource(str, Enum):
    """Origin of location coordinates."""
    GPS = "gps"
    USER_QUERY = "user_query"
    SAVED_PROFILE = "saved_profile"
    DISAMBIGUATION = "disambiguation"
