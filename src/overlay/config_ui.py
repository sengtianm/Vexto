import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv, set_key

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QMessageBox,
                             QScrollArea, QFrame, QTextEdit)
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
        self.setMinimumSize(450, 500)
        self.resize(500, 600)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # --- HEADER ---
        title = QLabel("🎙️ Vexto Dictation")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2C3E50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        self.status_label = QLabel("🔴 Detenido (Falta API Key)")
        self.status_label.setStyleSheet("font-size: 14px; color: #E74C3C; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # --- CONFIGURATION SECTION ---
        config_frame = QFrame()
        config_frame.setStyleSheet("background-color: #F8F9F9; border-radius: 8px; padding: 10px;")
        config_layout = QVBoxLayout(config_frame)
        
        # API Key Input
        key_layout = QHBoxLayout()
        key_label = QLabel("Groq API Key:")
        key_label.setStyleSheet("font-weight: bold;")
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Ingresa tu API Key de Groq...")
        
        current_key = os.getenv("GROQ_API_KEY", "")
        if current_key and current_key != "tu_clave_aqui":
            self.key_input.setText(current_key)
            
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        config_layout.addLayout(key_layout)
        
        # Hotkey Info
        hotq_layout = QHBoxLayout()
        hotq_label = QLabel("Atajo de Dictado:")
        hotq_label.setStyleSheet("font-weight: bold;")
        hotq_val = os.getenv("RECORD_HOTKEY", "ctrl+space")
        hotq_display = QLabel(f"<kbd>{hotq_val.upper()}</kbd>")
        hotq_display.setStyleSheet("background-color: #E5E7E9; color: #333; padding: 4px; border-radius: 4px; font-family: monospace;")
        hotq_layout.addWidget(hotq_label)
        hotq_layout.addWidget(hotq_display)
        hotq_layout.addStretch()
        config_layout.addLayout(hotq_layout)
        
        # Botones de Config
        self.save_btn = QPushButton("Guardar y Reiniciar")
        self.save_btn.setStyleSheet("background-color: #3498DB; color: white; padding: 8px; font-weight: bold; border-radius: 5px;")
        self.save_btn.clicked.connect(self.save_and_restart)
        config_layout.addWidget(self.save_btn)
        
        main_layout.addWidget(config_frame)

        # --- HISTORY SECTION ---
        hist_header_layout = QHBoxLayout()
        hist_title = QLabel("📝 Historial de Dictados")
        hist_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #34495E;")
        hist_header_layout.addWidget(hist_title)
        
        clear_hist_btn = QPushButton("Limpiar")
        clear_hist_btn.setStyleSheet("background-color: transparent; color: #7F8C8D; border: 1px solid #BDC3C7; padding: 4px 10px; border-radius: 4px;")
        clear_hist_btn.setMaximumWidth(80)
        clear_hist_btn.clicked.connect(self.clear_history)
        hist_header_layout.addWidget(clear_hist_btn)
        
        main_layout.addLayout(hist_header_layout)
        
        # Scroll Area for history
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #BDC3C7; border-radius: 8px; background-color: white; }")
        
        self.history_container = QWidget()
        self.history_container.setStyleSheet("background-color: white;")
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.history_container)
        main_layout.addWidget(self.scroll_area)

        # Load initial history
        self.refresh_history_ui()

        # --- FOOTER ---
        self.close_btn = QPushButton("🛑 CERRAR VEXTO COMPLETAMENTE")
        self.close_btn.setStyleSheet("background-color: #E74C3C; color: white; padding: 12px; font-weight: bold; border-radius: 5px; font-size: 13px;")
        self.close_btn.clicked.connect(self.close)
        main_layout.addWidget(self.close_btn)
        
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
            empty_lbl.setStyleSheet("color: #95A5A6; font-style: italic; padding: 20px;")
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
                header.setStyleSheet("font-weight: bold; color: #2980B9; margin-top: 10px; border-bottom: 1px solid #ECF0F1;")
                self.history_layout.addWidget(header)
                
            # Add Item
            self._add_history_item_widget(entry)

    def _add_history_item_widget(self, entry):
        item_frame = QFrame()
        item_frame.setStyleSheet("background-color: #FDFEFE; border: 1px solid #EAEDED; border-radius: 6px; margin-bottom: 5px;")
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(10, 8, 10, 8)
        
        # Time and Copy Row
        top_row = QHBoxLayout()
        
        time_lbl = QLabel(f"{entry.get('time', '')}")
        time_lbl.setStyleSheet("color: #7F8C8D; font-size: 11px; border: none;")
        top_row.addWidget(time_lbl)
        top_row.addStretch()
        
        copy_btn = QPushButton("Copiar")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("background-color: #ECF0F1; color: #2C3E50; border: none; padding: 3px 8px; border-radius: 4px; font-size: 11px;")
        
        # Inline function to handle copy
        def make_copy_func(text_to_copy):
            def copy_to_clipboard():
                QApplication.clipboard().setText(text_to_copy)
                copy_btn.setText("¡Copiado!")
            return copy_to_clipboard
            
        copy_btn.clicked.connect(make_copy_func(entry.get("text", "")))
        top_row.addWidget(copy_btn)
        
        item_layout.addLayout(top_row)
        
        # Text Content
        text_disp = QLabel(entry.get("text", ""))
        text_disp.setWordWrap(True)
        text_disp.setStyleSheet("color: #34495E; font-size: 13px; margin-top: 5px;")
        
        item_layout.addWidget(text_disp)
        
        self.history_layout.addWidget(item_frame)

    def clear_history(self):
        reply = QMessageBox.question(self, "Limpiar Historial", 
                                     "¿Estás seguro de que deseas borrar todos tus dictados guardados? Esta acción no se puede deshacer.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear()
            self.refresh_history_ui()

    def save_and_restart(self):
        new_key = self.key_input.text().strip()
        if not new_key:
            QMessageBox.warning(self, "Error", "Por favor ingresa tu API Key de Groq.")
            return
            
        set_key(self.env_path, "GROQ_API_KEY", new_key)
        self.start_backend()

    def start_backend(self):
        from main import start_background_services
        # Detener primero si ya está corriendo
        if self.hotkey_manager:
            self.hotkey_manager.stop()
            
        # Pasar a main la función que emite la señal del historial para que pueda inyectarle datos de forma segura (Thread-Safe QT)
        self.status_label.setText("🟢 Vexto ejecutándose (Escuchando atajo)")
        self.status_label.setStyleSheet("font-size: 14px; color: #27AE60; font-weight: bold;")
        
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
