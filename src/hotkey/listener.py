import time
import keyboard as kb # System-wide keyboard hook (requires admin or runs fine on user space mostly, much more reliable than pynput)
from typing import Callable, Optional, List, Any

class HotkeyManager:
    """Manages the global hotkey for push-to-talk using the 'keyboard' module for flawless Windows support."""
    def __init__(self, hotkey: str = 'ctrl+space') -> None:
        self.hotkey: str = hotkey.lower()
        self.is_pressed: bool = False
        self.on_press_callbacks: List[Callable[[], None]] = []
        self.on_release_callbacks: List[Callable[[], None]] = []
        self._hook: Optional[Any] = None
        self.last_toggle_time: float = 0.0

    def add_callbacks(self, on_press: Optional[Callable[[], None]], on_release: Optional[Callable[[], None]]) -> None:
        if on_press: self.on_press_callbacks.append(on_press)
        if on_release: self.on_release_callbacks.append(on_release)

    def _on_activate(self) -> None:
        if not self.is_pressed:
            print("[Hotkey] Grabando...")
            self.is_pressed = True
            for cb in self.on_press_callbacks: cb()

    def _on_deactivate(self) -> None:
        if self.is_pressed:
            print("[Hotkey] Procesando...")
            self.is_pressed = False
            for cb in self.on_release_callbacks: cb()

    def start(self) -> None:
        if self._hook is not None:
            return
            
        def on_activate() -> None:
            current_time = time.time()
            # Debounce: si ha pasado menos de 0.5s desde el último intento, ignorar
            if current_time - self.last_toggle_time < 0.5:
                return
            self.last_toggle_time = current_time
            
            # TOGGLE LOGIC: Alternamos el estado
            if not self.is_pressed:
                self._on_activate()
            else:
                self._on_deactivate()

        # Keyboard module maneja los strings directamente (e.g "ctrl+space")
        # suppress=True tells windows NOT to pass the shortcut to other apps, avoiding double-triggers
        self._hook = kb.add_hotkey(self.hotkey, on_activate, suppress=True)

    def stop(self) -> None:
        if self._hook is not None:
            kb.remove_hotkey(self._hook)
            self._hook = None
