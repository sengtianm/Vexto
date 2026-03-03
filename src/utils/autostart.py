import os
import winreg
from src.utils.paths import STARTUP_BAT

APP_NAME = "Vexto Dictation"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def get_bat_path() -> str:
    return STARTUP_BAT

def enable_autostart() -> bool:
    bat_path = get_bat_path()
    if not os.path.exists(bat_path):
        print(f"Error: No se encontró el archivo {bat_path}")
        return False
        
    try:
        # Wrap the path in quotes to handle spaces
        cmd = f'"{bat_path}"'
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        print("Autostart habilitado exitosamente en el registro.")
        return True
    except PermissionError:
        print("Error: Permisos insuficientes para modificar el registro de inicio de Windows.")
        return False
    except OSError as e:
        print(f"Error de sistema al habilitar autostart: {e}")
        return False

def disable_autostart() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
        try:
            winreg.DeleteValue(key, APP_NAME)
            print("Autostart deshabilitado del registro.")
        except FileNotFoundError:
            pass # Ya estaba borrado
        finally:
            winreg.CloseKey(key)
        return True
    except PermissionError:
        print("Error: Permisos insuficientes para modificar el registro de inicio de Windows.")
        return False
    except OSError as e:
        print(f"Error de sistema al deshabilitar autostart: {e}")
        return False

def is_autostart_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        bat_path = get_bat_path()
        return value == f'"{bat_path}"'
    except FileNotFoundError:
        return False
    except OSError as e:
        print(f"Aviso OS verificando estado autostart: {e}")
        return False
