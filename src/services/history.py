import os
import json
from datetime import datetime
from typing import List, Dict, Any
from src.utils import HISTORY_FILE

class HistoryManager:
    """Manages the local dictation history file."""
    
    def __init__(self) -> None:
        self.history_file = HISTORY_FILE
        
    def add_entry(self, text: str) -> None:
        if not text.strip(): return
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "words": len(text.split())
        }
        
        history = self.get_all()
        history.insert(0, entry) # add to beginning
        
        # Keep only last 100 entries to prevent oversized files
        if len(history) > 100:
            history = history[:100]
            
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"Error (OS) guardando historial: {e}")

    def get_all(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        return []

    def clear(self) -> None:
        if os.path.exists(self.history_file):
            try:
                os.remove(self.history_file)
            except OSError as e:
                print(f"Aviso OS borrando archivo de historial: {e}")
