import pyperclip
import keyboard
import time

class TextInjector:
    """Injects processed text securely into the currently active window."""
    
    def inject(self, text):
        if not text:
            return

        # 1. Guardar estado del portapapeles actual
        original_clipboard = pyperclip.paste()
        try:
            # 2. Copiar el nuevo texto al portapapeles
            pyperclip.copy(text)
            
            # Pequeña pausa para que OS registre el cambio de clipboard
            time.sleep(0.05)
            
            # 3. Simular pulsación de pegar (Ctrl+V)
            keyboard.send('ctrl+v')
            
            # 4. Necesario esperar a que la aplicación activa procese el pego antes de restaurar
            time.sleep(0.15)
        finally:
            # 5. Restaurar el portapapeles original para no ser invasivos con el workflow del usuario
            pyperclip.copy(original_clipboard)
