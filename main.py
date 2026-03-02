import os
import sys
import threading
from dotenv import load_dotenv

from PyQt6.QtWidgets import QApplication

from src.hotkey.listener import HotkeyManager
from src.audio.capture import AudioRecorder
from src.llm.provider import AIPipeline
from src.utils.injector import TextInjector
from src.overlay.ui import VextoOverlay

# Instancia global del Overlay para no recrearla múltiples veces
_overlay_instance = None

def get_overlay():
    global _overlay_instance
    if _overlay_instance is None:
        _overlay_instance = VextoOverlay()
    return _overlay_instance

def start_background_services(history_callback=None):
    """
    Inicializa los servicios de audio e IA en segundo plano
    y devuelve el manejador de atajos para poder detenerlo.
    """
    load_dotenv()
    hotkey = os.getenv("RECORD_HOTKEY", "ctrl+space")
    
    # Manejo del índice de micrófono opcional
    device_index_str = os.getenv("RECORD_DEVICE_INDEX", "")
    device_index = int(device_index_str) if device_index_str.isdigit() else None
    
    # Inicializar componentes
    recorder = AudioRecorder(device_index=device_index)
    pipeline = AIPipeline()
    injector = TextInjector()
    
    print(f"\n[Vexto] Background Services Iniciados.")
    print(f"[Vexto] Atajo: Presiona '{hotkey}' para iniciar/detener grabacion.")
    if device_index is not None:
        print(f"[Vexto] Micrófono forzado a ID: {device_index}\n")
    
    overlay = get_overlay()
    overlay.recorder_ref = recorder
    
    def on_press():
        overlay.signals.update_state.emit("listening")
        recorder.start()
        
    def on_release():
        overlay.signals.update_state.emit("processing")
        wav_path = recorder.stop()
        
        def process_audio():
            if wav_path and os.path.exists(wav_path):
                transcription = pipeline.transcribe_audio(wav_path)
                
                if transcription:
                    final_text = pipeline.rewrite_text(transcription)
                    injector.inject(final_text)
                    
                    # Log to history via callback to keep thread safety
                    if history_callback:
                        history_callback(final_text)
                        
                try:
                    os.remove(wav_path)
                except:
                    pass
                    
            overlay.signals.update_state.emit("idle")
            
        threading.Thread(target=process_audio, daemon=True).start()
        
    manager = HotkeyManager(hotkey=hotkey)
    manager.add_callbacks(on_press, on_release)
    manager.start()
    
    return manager


if __name__ == "__main__":
    # Arrancar la UI del panel de control
    from src.overlay.config_ui import main as ui_main
    ui_main()
