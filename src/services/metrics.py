import os
import json
from datetime import datetime
from typing import Dict, Any
from src.utils import PROJECT_ROOT, MetricsKeys

class DashboardMetricsService:
    """Respeta el SRP centralizando toda la lógica de cálculo estadístico."""
    
    def __init__(self):
        self.stats_file = os.path.join(PROJECT_ROOT, "user_stats.json")
        self.dictated_words = 0
        self.total_dictations = 0
        self.daily_streak = 0
        self.last_dictation_date = ""
        
        self.load_stats()
        self._check_streak_on_load()

    def load_stats(self) -> None:
        """Carga en memoria desde el archivo JSON exclusivo de estadísticas."""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.dictated_words = data.get(MetricsKeys.DICTATED_WORDS, 0)
                    self.total_dictations = data.get(MetricsKeys.TOTAL_DICTATIONS, 0)
                    self.daily_streak = data.get(MetricsKeys.DAILY_STREAK, 0)
                    self.last_dictation_date = data.get(MetricsKeys.LAST_DICTATION_DATE, "")
            except (OSError, json.JSONDecodeError) as e:
                print(f"[Vexto] Warning: No se pudieron cargar las estadísticas ({e}). Se usarán valores por defecto.")

    def save_stats(self) -> None:
        """Persiste al disco de forma atómica y segura."""
        data = {
            MetricsKeys.DICTATED_WORDS: self.dictated_words,
            MetricsKeys.TOTAL_DICTATIONS: self.total_dictations,
            MetricsKeys.DAILY_STREAK: self.daily_streak,
            MetricsKeys.LAST_DICTATION_DATE: self.last_dictation_date
        }
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"Error guardando estadísticas: {e}")

    def _check_streak_on_load(self) -> None:
        """Decide matemáticamente si la racha se perdió al abrir la app."""
        today_date_str = datetime.now().strftime("%Y-%m-%d")
        if self.last_dictation_date and self.last_dictation_date != today_date_str:
            try:
                today_dt = datetime.strptime(today_date_str, "%Y-%m-%d").date()
                last_dt = datetime.strptime(self.last_dictation_date, "%Y-%m-%d").date()
                diff = (today_dt - last_dt).days
                if diff > 1:
                    # La racha se ha perdido!
                    self.daily_streak = 0
                    self.save_stats()
            except ValueError:
                pass

    def add_dictation(self, text: str) -> None:
        """Procesa un nuevo dictado y recalcula matemáticamente contadores y rachas."""
        if not text.strip():
            return
            
        words_count = len(text.split())
        self.total_dictations += 1
        
        today_dt = datetime.now().date()
        today_str = today_dt.strftime("%Y-%m-%d")
        
        if self.last_dictation_date != today_str:
            if self.last_dictation_date:
                try:
                    last_dt = datetime.strptime(self.last_dictation_date, "%Y-%m-%d").date()
                    diff = (today_dt - last_dt).days
                    if diff == 1:
                        self.daily_streak += 1
                    elif diff > 1:
                        self.daily_streak = 1
                except ValueError:
                    self.daily_streak = 1
            else:
                self.daily_streak = 1
                
            self.last_dictation_date = today_str
            
        if words_count > 0:
            self.dictated_words += words_count
            
        self.save_stats()

    def get_time_saved_str(self) -> str:
        """Cálculo abstracto para la UI (aislando lógica de la vista)"""
        minutes = max(0.0, (self.dictated_words / 40.0) - (self.dictated_words / 150.0))
        if minutes < 60:
            return f"{int(minutes)} min"
        else:
            return f"{minutes/60:.1f} hrs"

    def reset_stats(self) -> None:
        """Limpia todo."""
        self.dictated_words = 0
        self.total_dictations = 0
        self.daily_streak = 0
        self.last_dictation_date = ""
        self.save_stats()
