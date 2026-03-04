import os
import json
from typing import Dict, Optional
from src.utils import PROJECT_ROOT
from src.utils import ConfigKeys

class AppSettingsService:
    """
    Servicio de Manejo de Configuraciones Volátiles del Usuario.
    Aísla las preferencias (atajos, idioma, autoarranque, etc.)
    para evitar escritura / sobreescritura constante en el archivo .env principal.
    """
    def __init__(self) -> None:
        self.config_file = os.path.join(PROJECT_ROOT, "config.user.json")
        self._cache: Dict[str, str] = {}
        self.load()

    def load(self) -> None:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                    
                # Rellenar con defaults si al archivo JSON le faltan llaves nuevas
                defaults = self._get_defaults()
                needs_save = False
                for k, v in defaults.items():
                    if k not in self._cache:
                        self._cache[k] = v
                        needs_save = True
                
                if needs_save:
                    self.save()
            except Exception:
                self._cache = self._get_defaults()
        else:
            self._cache = self._get_defaults()
            self.save()

    def _get_defaults(self) -> Dict[str, str]:
        return {
            ConfigKeys.RECORD_HOTKEY: "ctrl+space",
            ConfigKeys.RECORD_DEVICE_INDEX: "",
            ConfigKeys.RECORD_LANGUAGE: "es",
            ConfigKeys.SMART_FORMATTING: "True",
            ConfigKeys.AUTOSTART: "False"
        }

    def save(self) -> None:
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=4)
        except Exception as e:
            print(f"Error guardando app settings: {e}")

    def get(self, key: str) -> Optional[str]:
        return self._cache.get(key, self._get_defaults().get(key))

    def set(self, key: str, value: str) -> None:
        self._cache[key] = str(value)
        self.save()
