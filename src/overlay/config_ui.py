import os
import sys
from dotenv import load_dotenv, set_key

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt

class ControlPanelWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
        # Load existing or create empty
        if not os.path.exists(self.env_path):
            with open(self.env_path, 'w') as f:
                f.write("GROQ_API_KEY=\nRECORD_HOTKEY=ctrl+space\n")
        load_dotenv(self.env_path)
        
        # Referencias a procesos en background
        self.hotkey_manager = None
        
        self.init_ui()
        
        # Iniciar backend automáticamente si hay clave
        if os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "tu_clave_aqui":
            self.start_backend()

    def init_ui(self):
        self.setWindowTitle("Vexto - Panel de Control")
        self.setFixedSize(450, 260)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        title = QLabel("🎙️ Vexto Dictation")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2C3E50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Status
        self.status_label = QLabel("🔴 Detenido (Falta API Key)")
        self.status_label.setStyleSheet("font-size: 14px; color: #E74C3C; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # API Key Input
        key_layout = QHBoxLayout()
        key_label = QLabel("Groq API Key:")
        key_label.setStyleSheet("font-weight: bold;")
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Ingresa tu API Key de Groq...")
        
        # Load current key
        current_key = os.getenv("GROQ_API_KEY", "")
        if current_key and current_key != "tu_clave_aqui":
            self.key_input.setText(current_key)
            
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        layout.addLayout(key_layout)
        
        # Hotkey Info
        hotq_layout = QHBoxLayout()
        hotq_label = QLabel("Atajo de Dictado:")
        hotq_label.setStyleSheet("font-weight: bold;")
        
        hotq_val = os.getenv("RECORD_HOTKEY", "ctrl+space")
        hotq_display = QLabel(f"<kbd>{hotq_val.upper()}</kbd>")
        hotq_display.setStyleSheet("background-color: #EEE; color: #333; padding: 4px; border-radius: 4px; font-family: monospace;")
        hotq_layout.addWidget(hotq_label)
        hotq_layout.addWidget(hotq_display)
        hotq_layout.addStretch()
        layout.addLayout(hotq_layout)
        
        # Instrucciones
        inst = QLabel(f"Presiona <b>{hotq_val.upper()}</b> una vez para empezar a dictar. Vuelve a presionarlo para terminar y procesar el texto.")
        inst.setWordWrap(True)
        inst.setStyleSheet("color: #666; font-size: 12px;")
        inst.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(inst)
        
        # Botones
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Guardar Clave y Reiniciar")
        self.save_btn.setStyleSheet("background-color: #3498DB; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.save_btn.clicked.connect(self.save_and_restart)
        
        self.close_btn = QPushButton("🛑 Cerrar Vexto Completamente")
        self.close_btn.setStyleSheet("background-color: #E74C3C; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.close_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def save_and_restart(self):
        new_key = self.key_input.text().strip()
        if not new_key:
            QMessageBox.warning(self, "Error", "Por favor ingresa tu API Key de Groq.")
            return
            
        # Save to .env
        set_key(self.env_path, "GROQ_API_KEY", new_key)
        
        # Restart backend
        self.start_backend()

    def start_backend(self):
        from main import start_background_services
        # Detener primero si ya está corriendo
        if self.hotkey_manager:
            self.hotkey_manager.stop()
            
        # Iniciar
        self.status_label.setText("🟢 Vexto ejecutándose (Escuchando atajo)")
        self.status_label.setStyleSheet("font-size: 14px; color: #27AE60; font-weight: bold;")
        
        self.hotkey_manager = start_background_services()

    def closeEvent(self, event):
        """Asegurar que al presionar la 'X' o el botón cerrar, el hook se desactive y todo muera."""
        print("Cerrando Vexto por completo...")
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        QApplication.quit()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Fundamental: Hacer que al cerrar la última ventana (nuestro panel) se salga de la app
    app.setQuitOnLastWindowClosed(True)
    
    window = ControlPanelWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
