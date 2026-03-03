class AppState:
    """Estados del sistema de Grabación y Procesado."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    ERROR = "error"

class Models:
    """Nombres exactos de modelos LLM para la API."""
    WHISPER = "whisper-large-v3"
    LLAMA = "llama-3.3-70b-versatile"

class EnvVars:
    """Variables de entorno de estado en crudo usadas para comunicación de procesos."""
    WHISPER_KEY = "VEXTO_WHISPER_KEY"
    LLAMA_KEY = "VEXTO_LLAMA_KEY"
    ERROR_VAL = "ERROR"


class ConfigKeys:
    """Claves de variables de entorno para configuración estática (.env)."""
    GROQ_API_KEY = "GROQ_API_KEY"
    GROQ_API_KEY_2 = "GROQ_API_KEY_2"
    RECORD_HOTKEY = "RECORD_HOTKEY"
    RECORD_DEVICE_INDEX = "RECORD_DEVICE_INDEX"
    RECORD_LANGUAGE = "RECORD_LANGUAGE"
    SMART_FORMATTING = "SMART_FORMATTING"
    AUTOSTART = "AUTOSTART"
    
class MetricsKeys:
    """Claves de variables de entorno estáticas de las estadísticas en Dashboard."""
    DICTATED_WORDS = "dictated_words"
    TOTAL_DICTATIONS = "total_dictations"
    DAILY_STREAK = "daily_streak"
    LAST_DICTATION_DATE = "last_dictation_date"
