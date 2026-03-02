import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv, set_key

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QMessageBox,
                             QScrollArea, QFrame, QTextEdit, QInputDialog, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal

class HistoryManager:
    """Manages the local dictation history file."""
    def __init__(self):
        self.history_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'historial.json')
        
    def add_entry(self, text):
        if not text.strip(): return
        
        history = self.get_all()
        
        # New entry with timestamp
        now = datetime.now()
        entry = {
            "text": text,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%I:%M %p")
        }
        
        history.insert(0, entry) # Insert at beginning
        
        # Keep only last 100 entries to prevent infinite growth
        history = history[:100]
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando historial: {e}")

    def get_all(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []

    def clear(self):
        if os.path.exists(self.history_file):
            try:
                os.remove(self.history_file)
            except:
                pass


class ControlPanelWindow(QWidget):
    # Definir señal para poder agregar texto al historial desde el hilo secundario
    add_history_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
        # Load existing or create empty
        if not os.path.exists(self.env_path):
            with open(self.env_path, 'w') as f:
                f.write("GROQ_API_KEY=\nRECORD_HOTKEY=ctrl+space\n")
        load_dotenv(self.env_path)
        
        self.history_manager = HistoryManager()
        self.hotkey_manager = None
        
        # Connect signal
        self.add_history_signal.connect(self.on_new_dictation)
        
        self.init_ui()
        
        # Iniciar backend automáticamente si hay clave
        if os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "tu_clave_aqui":
            self.start_backend()

    def init_ui(self):
        self.setWindowTitle("Vexto - Panel de Control")
        self.setMinimumSize(480, 550)
        self.resize(500, 650)
        
        # Estilo Global Premium Oscuro
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #E5E7EB; font-family: 'Segoe UI', Inter, Roboto, sans-serif; font-size: 14px; }
            QLineEdit { background-color: #27273A; border: 1px solid #3F3F5A; border-radius: 6px; padding: 8px; color: #FFFFFF; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #6366F1; background-color: #2A2A40; }
            QPushButton { border: none; font-weight: bold; border-radius: 6px; padding: 8px 16px; font-size: 13px; }
            QScrollArea { border: 1px solid #27273A; border-radius: 8px; background-color: #1E1E2E; }
            QScrollBar:vertical { border: none; background: #121212; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #3F3F5A; min-height: 30px; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: #555570; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; height: 0px; }
            QComboBox { background-color: #27273A; border: 1px solid #3F3F5A; border-radius: 6px; padding: 6px 10px; color: #FFFFFF; font-size: 13px; font-weight: bold; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox::down-arrow { image: none; }
            QComboBox QAbstractItemView { background-color: #1E1E2E; border: 1px solid #3F3F5A; selection-background-color: #4F46E5; color: #E5E7EB; border-radius: 4px; padding: 4px; }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)
        
        # --- HEADER ---
        title = QLabel("🎙️ Vexto Dictation")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF; letter-spacing: 0.5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # --- CONFIGURATION SECTION ---
        config_header_layout = QHBoxLayout()
        config_header_layout.setContentsMargins(4, 0, 4, 0)
        config_title = QLabel("⚙️ Configuración")
        config_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF; background: transparent;")
        config_header_layout.addWidget(config_title)
        
        main_layout.addLayout(config_header_layout)
        
        config_frame = QFrame()
        config_frame.setStyleSheet("QFrame { background-color: #1E1E2E; border: 1px solid #27273A; border-radius: 12px; padding: 12px; }")
        config_layout = QVBoxLayout(config_frame)
        config_layout.setSpacing(12)
        
        # Hotkey Info
        hotq_layout = QHBoxLayout()
        hotq_label = QLabel("Atajo de Dictado:")
        hotq_label.setStyleSheet("font-weight: bold; color: #9CA3AF; font-size: 13px; background: transparent; border: none;")
        hotq_val = os.getenv("RECORD_HOTKEY", "ctrl+space")
        self.hotq_display = QLabel(f"{hotq_val.upper()}")
        self.hotq_display.setStyleSheet("background-color: #27273A; color: #6366F1; padding: 4px 10px; border-radius: 6px; font-family: monospace; font-weight: bold; border: 1px solid #3F3F5A;")
        
        edit_hotq_btn = QPushButton("✎ Cambiar")
        edit_hotq_btn.setStyleSheet("QPushButton { background-color: transparent; color: #818CF8; border: 1px solid #3F3F5A; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; } QPushButton:hover { background-color: #27273A; color: #A5B4FC; }")
        edit_hotq_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_hotq_btn.clicked.connect(self.change_hotkey)
        
        hotq_layout.addWidget(hotq_label)
        hotq_layout.addWidget(self.hotq_display)
        hotq_layout.addWidget(edit_hotq_btn)
        hotq_layout.addStretch()
        config_layout.addLayout(hotq_layout)
        
        # Microphone Device Selector
        mic_layout = QHBoxLayout()
        mic_label = QLabel("Micrófono:")
        mic_label.setStyleSheet("font-weight: bold; color: #9CA3AF; font-size: 13px; background: transparent; border: none;")
        self.mic_combo = QComboBox()
        self.mic_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_combo.setMinimumWidth(250)
        
        # Populate Mics
        from src.audio.capture import AudioRecorder
        self.mics_list = AudioRecorder.get_microphones()
        
        current_mic_idx_str = os.getenv("RECORD_DEVICE_INDEX", "")
        current_mic_idx = int(current_mic_idx_str) if current_mic_idx_str.isdigit() else None
        
        self.mic_combo.addItem("Predeterminado del Sistema", -1)
        for mic in self.mics_list:
            self.mic_combo.addItem(mic['name'], mic['id'])
            
        # Set current selection
        if current_mic_idx is not None:
            index = self.mic_combo.findData(current_mic_idx)
            if index >= 0:
                self.mic_combo.setCurrentIndex(index)
                
        # Connect change event
        self.mic_combo.currentIndexChanged.connect(self.change_microphone)
        
        mic_layout.addWidget(mic_label)
        mic_layout.addWidget(self.mic_combo)
        mic_layout.addStretch()
        config_layout.addLayout(mic_layout)
        
        # Language Selector
        lang_layout = QHBoxLayout()
        lang_label = QLabel("Idioma:")
        lang_label.setStyleSheet("font-weight: bold; color: #9CA3AF; font-size: 13px; background: transparent; border: none;")
        self.lang_combo = QComboBox()
        self.lang_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_combo.setMinimumWidth(250)
        
        self.lang_combo.addItem("Español", "es")
        self.lang_combo.addItem("Inglés", "en")
        
        current_lang = os.getenv("RECORD_LANGUAGE", "es")
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
            
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        
        # Guardado en variable de clase para evitar disparos accidentales
        self.current_lang = current_lang
        
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        config_layout.addLayout(lang_layout)
        
        # Smart Formatting Selector (Fase 3)
        format_layout = QHBoxLayout()
        format_layout.setContentsMargins(0, 10, 0, 0)
        self.format_checkbox = QCheckBox("🪄 Formateo Inteligente (Listas y Párrafos Automáticos)")
        self.format_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.format_checkbox.setStyleSheet("QCheckBox { color: #818CF8; font-weight: bold; font-size: 13px; background: transparent; border: none; } QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #3F3F5A; border-radius: 4px; background: #27273A; } QCheckBox::indicator:checked { background: #4F46E5; }")
        
        smart_formatting_env = os.getenv("SMART_FORMATTING", "False").lower() == "true"
        self.format_checkbox.setChecked(smart_formatting_env)
        self.format_checkbox.stateChanged.connect(self.change_formatting_state)
        
        format_layout.addWidget(self.format_checkbox)
        format_layout.addStretch()
        config_layout.addLayout(format_layout)
        
        # Autostart Selector (Fase 6)
        auto_layout = QHBoxLayout()
        auto_layout.setContentsMargins(0, 5, 0, 0)
        self.auto_checkbox = QCheckBox("🚀 Arrancar Vexto al iniciar Windows")
        self.auto_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auto_checkbox.setStyleSheet("QCheckBox { color: #818CF8; font-weight: bold; font-size: 13px; background: transparent; border: none; } QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #3F3F5A; border-radius: 4px; background: #27273A; } QCheckBox::indicator:checked { background: #4F46E5; }")
        
        # Leemos el estado real del registro por seguridad, o el .env
        import src.utils.autostart as autostart
        is_auto = autostart.is_autostart_enabled()
        # Reparamos el .env si no coincide
        set_key(self.env_path, "AUTOSTART", "True" if is_auto else "False")
        
        self.auto_checkbox.setChecked(is_auto)
        self.auto_checkbox.stateChanged.connect(self.change_autostart_state)
        
        auto_layout.addWidget(self.auto_checkbox)
        auto_layout.addStretch()
        config_layout.addLayout(auto_layout)
        
        # Settings are now managed exclusively in .env file
        
        main_layout.addWidget(config_frame)

        # --- HISTORY SECTION ---
        hist_header_layout = QHBoxLayout()
        hist_header_layout.setContentsMargins(4, 10, 4, 0)
        hist_title = QLabel("📝 Historial de Dictados")
        hist_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF; background: transparent;")
        hist_header_layout.addWidget(hist_title)
        
        clear_hist_btn = QPushButton("Limpiar")
        clear_hist_btn.setStyleSheet("QPushButton { background-color: transparent; color: #9CA3AF; border: 1px solid #3F3F5A; padding: 4px 12px; border-radius: 6px; font-size: 12px; } QPushButton:hover { background-color: #27273A; color: #E5E7EB; }")
        clear_hist_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_hist_btn.setMaximumWidth(80)
        clear_hist_btn.clicked.connect(self.clear_history)
        hist_header_layout.addWidget(clear_hist_btn)
        
        main_layout.addLayout(hist_header_layout)
        
        # Scroll Area for history
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # remove inline style as global style takes over
        
        self.history_container = QWidget()
        self.history_container.setStyleSheet("background-color: #1E1E2E;")
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.history_layout.setSpacing(10)
        self.history_layout.setContentsMargins(12, 12, 12, 12)
        
        self.scroll_area.setWidget(self.history_container)
        main_layout.addWidget(self.scroll_area)

        # Load initial history
        self.refresh_history_ui()

        # --- FOOTER ---
        # El cierre ahora se maneja nativamente mediante la "X" de la ventana.
        
        self.setLayout(main_layout)

    def on_new_dictation(self, text):
        """Called automatically via signal when a new dictation finishes"""
        self.history_manager.add_entry(text)
        self.refresh_history_ui()

    def refresh_history_ui(self):
        """Clears and rebuilds the history list based on local file"""
        # Clear current layout
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        entries = self.history_manager.get_all()
        
        if not entries:
            empty_lbl = QLabel("No hay dictados recientes.")
            empty_lbl.setStyleSheet("color: #6B7280; font-style: italic; font-size: 13px; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_layout.addWidget(empty_lbl)
            return

        # Group by Date
        current_date_group = None
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        for entry in entries:
            date_str = entry.get("date")
            
            # Add Header if date changed
            if date_str != current_date_group:
                current_date_group = date_str
                
                header = QLabel("Hoy" if date_str == today_str else date_str)
                header.setStyleSheet("font-weight: bold; color: #818CF8; margin-top: 12px; margin-bottom: 4px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; background: transparent;")
                self.history_layout.addWidget(header)
                
            # Add Item
            self._add_history_item_widget(entry)

    def _add_history_item_widget(self, entry):
        item_frame = QFrame()
        item_frame.setStyleSheet("QFrame { background-color: #27273A; border: 1px solid #3F3F5A; border-radius: 8px; }")
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(14, 12, 14, 12)
        item_layout.setSpacing(8)
        
        # Time and Copy Row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0,0,0,0)
        
        time_lbl = QLabel(f"{entry.get('time', '')}")
        time_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px; border: none; font-weight: bold; background: transparent;")
        top_row.addWidget(time_lbl)
        top_row.addStretch()
        
        copy_btn = QPushButton("Copiar")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("QPushButton { background-color: #374151; color: #D1D5DB; border: none; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; } QPushButton:hover { background-color: #4B5563; color: white; }")
        
        # Inline function to handle copy
        def make_copy_func(text_to_copy):
            def copy_to_clipboard():
                QApplication.clipboard().setText(text_to_copy)
                copy_btn.setText("✓ Copiado")
                copy_btn.setStyleSheet("QPushButton { background-color: #059669; color: white; border: none; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; }")
            return copy_to_clipboard
            
        copy_btn.clicked.connect(make_copy_func(entry.get("text", "")))
        top_row.addWidget(copy_btn)
        
        item_layout.addLayout(top_row)
        
        # Text Content
        text_disp = QLabel(entry.get("text", ""))
        text_disp.setWordWrap(True)
        text_disp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_disp.setStyleSheet("color: #E5E7EB; font-size: 13px; line-height: 1.4; border: none; background: transparent;")
        
        item_layout.addWidget(text_disp)
        
        self.history_layout.addWidget(item_frame)

    def clear_history(self):
        reply = QMessageBox.question(self, "Limpiar Historial", 
                                     "¿Estás seguro de que deseas borrar todos tus dictados guardados? Esta acción no se puede deshacer.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear()
            self.refresh_history_ui()



    def change_hotkey(self):
        current = os.getenv("RECORD_HOTKEY", "ctrl+space")
        text, ok = QInputDialog.getText(self, 'Cambiar Atajo', 
            'Ingresa el nuevo atajo:\n(Ejemplos: ctrl+space, alt+x, ctrl+shift+a)',
            QLineEdit.EchoMode.Normal, current)
            
        if ok and text.strip():
            new_hotkey = text.strip().lower()
            # 1. Update UI
            self.hotq_display.setText(new_hotkey.upper())
            # 2. Update .env
            set_key(self.env_path, "RECORD_HOTKEY", new_hotkey)
            # 3. Update memory env so main.py reads it fresh
            os.environ["RECORD_HOTKEY"] = new_hotkey
            # 4. Reload backend if active
            if self.hotkey_manager:
                print(f"Reiniciando backend con nuevo atajo: {new_hotkey}")
                self.start_backend()

    def change_microphone(self, index):
        mic_id_data = self.mic_combo.itemData(index)
        
        if mic_id_data == -1: 
            # Predeterminado
            set_key(self.env_path, "RECORD_DEVICE_INDEX", "")
            os.environ["RECORD_DEVICE_INDEX"] = ""
            print("Micrófono cambiado a: Predeterminado")
        else:
            # Especifico
            set_key(self.env_path, "RECORD_DEVICE_INDEX", str(mic_id_data))
            os.environ["RECORD_DEVICE_INDEX"] = str(mic_id_data)
            print(f"Micrófono cambiado a ID: {mic_id_data}")
            
        if self.hotkey_manager:
            self.start_backend()

    def change_language(self, index):
        lang_data = self.lang_combo.itemData(index)
        
        if lang_data == self.current_lang:
            return
            
        self.current_lang = lang_data
        
        # Bloquear señales momentaneamente para evitar bucles durante el reload
        self.lang_combo.blockSignals(True)
        set_key(self.env_path, "RECORD_LANGUAGE", lang_data)
        os.environ["RECORD_LANGUAGE"] = lang_data
        
        print(f"Idioma cambiado a: {lang_data}")
        # En el caso del idioma, ni siquiera hace falta reiniciar el Thread entero,
        # pero reiniciar asegura un estado limpio de todo.
        if self.hotkey_manager:
            self.start_backend()
            
        self.lang_combo.blockSignals(False)

    def change_formatting_state(self, state):
        is_checked = bool(state == Qt.CheckState.Checked.value or state == 2)
        val_str = "True" if is_checked else "False"
        set_key(self.env_path, "SMART_FORMATTING", val_str)
        os.environ["SMART_FORMATTING"] = val_str
        print(f"Formateo Inteligente: {val_str}")
        # Llama 3 lee os.getenv("SMART_FORMATTING") en cada dictado en provider.py,
        # por lo que no es estrictamente necesario reiniciar el hilo de captura de audio.

    def change_autostart_state(self, state):
        import src.utils.autostart as autostart
        is_checked = bool(state == Qt.CheckState.Checked.value or state == 2)
        val_str = "True" if is_checked else "False"
        
        # Impact registry OS Level
        if is_checked:
            autostart.enable_autostart()
        else:
            autostart.disable_autostart()
            
        # Update Persistency
        set_key(self.env_path, "AUTOSTART", val_str)
        os.environ["AUTOSTART"] = val_str
        print(f"Arrancar con Windows: {val_str}")

    def start_backend(self):
        from main import start_background_services
        # Detener primero si ya está corriendo
        if self.hotkey_manager:
            self.hotkey_manager.stop()
            
        # Pasar a main la función que emite la señal del historial para que pueda inyectarle datos de forma segura (Thread-Safe QT)
        
        # Importante: inyectamos la llamada `add_history_signal.emit` a los servicios en background
        self.hotkey_manager = start_background_services(history_callback=self.add_history_signal.emit)

    def closeEvent(self, event):
        print("Cerrando Vexto por completo...")
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        QApplication.quit()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    window = ControlPanelWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
