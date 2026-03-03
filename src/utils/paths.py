import os

# --- CONTEXTO DEL PROYECTO ---
# __file__ es .../src/utils/paths.py
# dir(__file__) es .../src/utils
# dir(dir(__file__)) es .../src
# dir(dir(dir(__file__))) es .../Vexto (Raíz del proyecto)
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- RUTAS A RECURSOS COMUNES ---
ENV_FILE: str = os.path.join(PROJECT_ROOT, '.env')
HISTORY_FILE: str = os.path.join(PROJECT_ROOT, 'historial.json')
LOGO_ICON: str = os.path.join(PROJECT_ROOT, 'src', 'assets', 'logo3.svg')

# --- RUTAS DE EJECUCIÓN ---
STARTUP_BAT: str = os.path.join(PROJECT_ROOT, 'iniciar vexto.bat')
