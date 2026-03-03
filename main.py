import os
import sys
import concurrent.futures
from dotenv import load_dotenv
from typing import Optional, Callable, Any
from src.utils.constants import AppState, ConfigKeys

from PyQt6.QtWidgets import QApplication

from src.hotkey import HotkeyManager
from src.audio import AudioRecorder
from src.llm import AIPipeline
from src.utils import TextInjector
from src.overlay import VextoOverlay
from src.services import AppSettingsService

# Instancia global del Overlay para no recrearla múltiples veces
_overlay_instance = None

def get_overlay() -> VextoOverlay:
    global _overlay_instance
    if _overlay_instance is None:
        _overlay_instance = VextoOverlay()
    return _overlay_instance

# Gestor global de hilos para encolar dictados (Graceful Shutdown)
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="VextoWorker")

def start_background_services(history_callback: Optional[Callable[[str], None]] = None) -> HotkeyManager:
    """
    Inicializa los servicios de audio e IA en segundo plano
    y devuelve el manejador de atajos para poder detenerlo.
    """
    load_dotenv()
    
    app_settings = AppSettingsService()
    hotkey = app_settings.get(ConfigKeys.RECORD_HOTKEY)
    
    # Manejo del índice de micrófono opcional
    device_index_str = app_settings.get(ConfigKeys.RECORD_DEVICE_INDEX)
    device_index = int(device_index_str) if device_index_str and device_index_str.isdigit() else None
    
    # Inicializar componentes
    recorder = AudioRecorder(device_index=device_index)
    pipeline = AIPipeline()
    injector = TextInjector()
    
    print(f"\n[Vexto] Background Services Iniciados.")
    print(f"[Vexto] Atajo: Presiona '{hotkey}' para iniciar/detener grabacion.")
    if device_index is not None:
        print(f"[Vexto] Micrófono forzado a ID: {device_index}\n")
    
    overlay = get_overlay()
    recorder.on_volume_change = lambda vol: overlay.signals.update_volume.emit(vol)
    
    def on_press() -> None:
        overlay.signals.update_state.emit(AppState.LISTENING)
        recorder.start()
        
    def on_release() -> None:
        overlay.signals.update_state.emit(AppState.PROCESSING)
        wav_path = recorder.stop()
        
        def process_audio() -> None:
            success = False
            try:
                if wav_path and os.path.exists(wav_path):
                    transcription = pipeline.transcribe_audio(wav_path)
                    
                    if transcription:
                        is_formatting_on = app_settings.get(ConfigKeys.SMART_FORMATTING).lower() == "true"
                        if is_formatting_on:
                            final_text = pipeline.rewrite_text(transcription)
                        else:
                            final_text = transcription
                            
                        if final_text and final_text.strip():
                            # Añadir espacio final automáticamente
                            if not final_text.endswith(" "):
                                final_text += " "
                                
                            injector.inject(final_text)
                            
                            # Log to history via callback to keep thread safety
                            if history_callback:
                                history_callback(final_text)
                            success = True
                        else:
                            # Fallo del LLM (devuelve vacío por reglas muy estrictas)
                            if history_callback:
                                history_callback("")
                    else:
                        # Garantizar que la UI se entere del fallo total del ASR
                        if history_callback:
                            history_callback("")
            except Exception as e:
                print(f"[Error] Excepción inesperada en hilo secundario: {e}")
            finally:
                if wav_path and os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                    except OSError as e:
                        print(f"Warning: No se pudo eliminar el archivo de audio temporal: {e}")
                    
                if success:
                    overlay.signals.update_state.emit(AppState.IDLE)
                else:
                    overlay.signals.update_state.emit(AppState.ERROR)
            
        _executor.submit(process_audio)
        
    manager = HotkeyManager(hotkey=hotkey)
    manager.add_callbacks(on_press, on_release)
    manager.start()
    
    return manager

def stop_background_services(manager: Optional[HotkeyManager]) -> None:
    """Implementa un apagado elegante, esperando a que terminen los audios encolados."""
    print("\n[Vexto] Deteniendo manejador de atajos...")
    if manager:
        manager.stop()
        
    print("[Vexto] Esperando a que finalicen las tareas de IA pendientes (Graceful Shutdown)...")
    _executor.shutdown(wait=True)
    print("[Vexto] Hilos secundarios limpiados exitosamente.")

if __name__ == "__main__":
    # Arrancar la UI del panel de control
    from src.overlay.config_ui import main as ui_main
    ui_main()
