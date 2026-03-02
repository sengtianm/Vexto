import os
import winreg

APP_NAME = "Vexto Dictation"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def get_bat_path():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(project_root, "iniciar vexto.bat")

def enable_autostart():
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
    except Exception as e:
        print(f"Error al habilitar autostart: {e}")
        return False

def disable_autostart():
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
    except Exception as e:
        print(f"Error al deshabilitar autostart: {e}")
        return False

def is_autostart_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        bat_path = get_bat_path()
        return value == f'"{bat_path}"'
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"Error verificando autostart: {e}")
        return False
