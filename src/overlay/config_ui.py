import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv, set_key

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QMessageBox,
                             QScrollArea, QFrame, QTextEdit, QInputDialog, QComboBox, QCheckBox,
                             QSystemTrayIcon, QMenu, QStyle, QGridLayout)
from PyQt6.QtGui import QIcon, QAction, QPixmap
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
        self.setup_tray()
        
        # Iniciar backend automáticamente si hay clave
        if os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "tu_clave_aqui":
            self.start_backend()

    def init_ui(self):
        self.setWindowTitle("Vexto - Panel de Control")
        # Diseño base cuadrado (Square UI), desbloqueando el límite vertical para manipulación del usuario
        self.setMinimumSize(540, 460)
        self.resize(560, 580)
        
        # Estilo Global Premium Oscuro
        self.setStyleSheet("""
            QWidget { background-color: #242124; color: #E5E4E2; font-family: 'Segoe UI', Inter, Roboto, sans-serif; font-size: 13px; }
            QLineEdit { background-color: #242124; border: 1px solid #242124; border-radius: 6px; padding: 10px; color: #E5E4E2; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #FFBA00; background-color: #242124; }
            QPushButton { border: none; background-color: #242124; color: #E5E4E2; font-weight: bold; border-radius: 6px; padding: 10px 18px; font-size: 13px; }
            QPushButton:hover { background-color: #FFBA00; color: #242124; }
            QScrollArea { border: none; border-radius: 8px; background-color: transparent; }
            QScrollBar:vertical { border: none; background: #242124; width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #555555; min-height: 30px; border-radius: 3px; }
            QScrollBar::handle:vertical:hover { background: #FFBA00; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; height: 0px; }
            QComboBox { background-color: #242124; border: 1px solid #242124; border-radius: 6px; padding: 10px 14px; color: #E5E4E2; font-size: 14px; }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow { image: none; }
            QComboBox QAbstractItemView { background-color: #242124; border: 1px solid #555555; selection-background-color: #555555; selection-color: #FFBA00; color: #E5E4E2; border-radius: 6px; padding: 6px; }
            QCheckBox { spacing: 10px; }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(35, 35, 35, 35)
        main_layout.setSpacing(12)
        
        # --- HEADER ---
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.setContentsMargins(4, 0, 0, 0)
        
        title = QLabel("Vexto")
        title.setStyleSheet("font-size: 42px; font-weight: 900; font-family: 'Segoe UI Black', Arial, sans-serif; color: #E5E4E2; letter-spacing: 2px;")
        
        # Align left dynamically
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # --- DASHBOARD (Grid 2x2) ---
        dashboard_layout = QGridLayout()
        dashboard_layout.setSpacing(8)
        dashboard_layout.setContentsMargins(0, 0, 0, 10)
        
        def create_stat_card(title, value, subtitle, val_color="#E5E4E2"):
            card = QFrame()
            card.setStyleSheet("QFrame { background-color: #383838; border-radius: 8px; }")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 12, 15, 12)
            c_layout.setSpacing(2)
            
            lbl_title = QLabel(title.upper())
            lbl_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #E5E4E2; letter-spacing: 1px; opacity: 0.6; background: transparent;")
            
            lbl_val = QLabel(value)
            lbl_val.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {val_color}; background: transparent; border: none;")
            
            lbl_sub = QLabel(subtitle)
            lbl_sub.setWordWrap(True)
            lbl_sub.setStyleSheet("font-size: 11px; color: #E5E4E2; opacity: 0.5; background: transparent;")
            
            c_layout.addWidget(lbl_title)
            c_layout.addWidget(lbl_val)
            c_layout.addWidget(lbl_sub)
            return card, lbl_val, lbl_sub
            
        self.dictated_words = int(os.getenv("DICTATED_WORDS", "0"))
        self.total_dictations = int(os.getenv("TOTAL_DICTATIONS", "0"))
        self.daily_streak = int(os.getenv("DAILY_STREAK", "0"))
        self.last_dictation_date = os.getenv("LAST_DICTATION_DATE", "")
        
        # Check streak on load
        today_date_str = datetime.now().strftime("%Y-%m-%d")
        if self.last_dictation_date:
            try:
                last_dt = datetime.strptime(self.last_dictation_date, "%Y-%m-%d").date()
                today_dt = datetime.now().date()
                diff = (today_dt - last_dt).days
                if diff > 1:
                    self.daily_streak = 0
                    set_key(self.env_path, "DAILY_STREAK", "0")
                    os.environ["DAILY_STREAK"] = "0"
            except:
                pass
                
        def get_time_saved_str(words):
            minutes = max(0.0, (words / 40.0) - (words / 150.0))
            if minutes < 60:
                return f"{int(minutes)} min"
            else:
                return f"{minutes/60:.1f} hrs"
                
        self.card_streak, self.lbl_streak, _ = create_stat_card("Racha Diaria", f"{self.daily_streak} día{'s' if self.daily_streak != 1 else ''} 🔥", "¡Sigue así!", "#FFBA00")
        self.card_time, self.lbl_time, _ = create_stat_card("Tiempo Ahorrado", get_time_saved_str(self.dictated_words), "Neto vs Manual")
        self.card_words, self.lbl_words, _ = create_stat_card("Palabras", f"{self.dictated_words:,}", "Dictadas en total")
        self.card_dicts, self.lbl_dicts, _ = create_stat_card("Dictados", f"{self.total_dictations:,}", "Disparos totales")
        
        dashboard_layout.addWidget(self.card_streak, 0, 0)
        dashboard_layout.addWidget(self.card_time, 0, 1)
        dashboard_layout.addWidget(self.card_words, 1, 0)
        dashboard_layout.addWidget(self.card_dicts, 1, 1)
        
        # --- HORIZONTAL AI MONITOR ---
        self.monitor_card = QFrame()
        self.monitor_card.setStyleSheet("QFrame { background-color: #383838; border-radius: 8px; }")
        
        self.monitor_layout = QHBoxLayout(self.monitor_card)
        self.monitor_layout.setContentsMargins(15, 8, 15, 8)
        self.monitor_layout.setSpacing(15)
        self.monitor_layout.addStretch()
        
        def update_dot_color(lbl, target_num, current_key):
            color = "#FFBA00" if current_key == target_num else "#D32F2F" if (target_num == "1" and current_key in ["2", "ERROR"]) or current_key == "ERROR" else "#E5E4E2"
            lbl.setStyleSheet(f"font-size: 16px; background: transparent; color: {color};")
            
        def create_indicator(text):
            h_layout = QHBoxLayout()
            h_layout.setSpacing(4)
            h_layout.setContentsMargins(0, 0, 0, 0)
            
            lbl_txt = QLabel(text)
            lbl_txt.setStyleSheet("font-size: 13px; color: #E5E4E2; background: transparent; font-weight: bold;")
            lbl_txt.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            
            lbl_dot = QLabel("●")
            lbl_dot.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            
            h_layout.addWidget(lbl_txt)
            h_layout.addWidget(lbl_dot)
            self.monitor_layout.addLayout(h_layout)
            return lbl_dot
            
        self.dot_w1 = create_indicator("Whisper (L1)")
        self.dot_w2 = create_indicator("Whisper (L2)")
        self.dot_l1 = create_indicator("Llama 70B (L1)")
        self.dot_l2 = create_indicator("Llama 70B (L2)")
        
        w_key = os.environ.get("VEXTO_WHISPER_KEY", "1")
        l_key = os.environ.get("VEXTO_LLAMA_KEY", "1")
        update_dot_color(self.dot_w1, "1", w_key)
        update_dot_color(self.dot_w2, "2", w_key)
        update_dot_color(self.dot_l1, "1", l_key)
        update_dot_color(self.dot_l2, "2", l_key)
        
        self.monitor_layout.addStretch()
        
        # Insertar exactamente en el Grid superior (fila 2, col 0, span_row 1, span_col 2) para mismas márgenes
        dashboard_layout.addWidget(self.monitor_card, 2, 0, 1, 2)
        
        main_layout.addLayout(dashboard_layout)
        
        # --- CONFIGURATION SECTION ---
        config_header_layout = QHBoxLayout()
        config_header_layout.setContentsMargins(4, 0, 4, 0)
        
        self.config_title_btn = QPushButton("▶ Configuración General")
        self.config_title_btn.setStyleSheet("font-size: 14px; font-weight: bold; color: #E5E4E2; background: transparent; text-align: left; text-transform: uppercase; letter-spacing: 1.5px; border: none; padding: 0;")
        self.config_title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_title_btn.clicked.connect(self.toggle_config_section)
        
        config_header_layout.addWidget(self.config_title_btn)
        config_header_layout.addStretch()
        
        main_layout.addLayout(config_header_layout)
        
        self.config_frame = QFrame()
        config_frame = self.config_frame
        config_frame.setObjectName("ConfigFrame")
        config_frame.setStyleSheet("#ConfigFrame { background-color: #383838; border: none; border-radius: 12px; }")
        config_layout = QVBoxLayout(config_frame)
        config_layout.setContentsMargins(20, 24, 20, 24)
        config_layout.setSpacing(16)
        
        # Hotkey Info
        hotq_layout = QHBoxLayout()
        hotq_label = QLabel("Atajo de Dictado")
        hotq_label.setStyleSheet("color: #E5E4E2; font-size: 14px; background: transparent; border: none; font-weight: bold;")
        hotq_label.setFixedWidth(115)
        hotq_val = os.getenv("RECORD_HOTKEY", "ctrl+space")
        self.hotq_display = QLabel(f"{hotq_val.upper()}")
        self.hotq_display.setStyleSheet("background-color: #242124; color: #FFBA00; padding: 8px 14px; border-radius: 6px; font-family: monospace; font-weight: bold; border: none;")
        
        edit_hotq_btn = QPushButton("Cambiar Atajo")
        edit_hotq_btn.setStyleSheet("QPushButton { background-color: transparent; color: #FFBA00; border: none; font-size: 13px; font-weight: bold; text-decoration: underline; padding: 0px; } QPushButton:hover { color: #E5E4E2; }")
        edit_hotq_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_hotq_btn.clicked.connect(self.change_hotkey)
        
        hotq_layout.addWidget(hotq_label)
        hotq_layout.addWidget(self.hotq_display)
        hotq_layout.addWidget(edit_hotq_btn)
        hotq_layout.addStretch()
        config_layout.addLayout(hotq_layout)
        
        # Microphone Device Selector
        mic_layout = QHBoxLayout()
        mic_label = QLabel("Micrófono")
        mic_label.setStyleSheet("color: #E5E4E2; font-size: 14px; background: transparent; border: none; font-weight: bold;")
        mic_label.setFixedWidth(115)
        self.mic_combo = QComboBox()
        self.mic_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_combo.setFixedWidth(330)
        self.mic_combo.setStyleSheet("QComboBox { background-color: #242124; border: none; border-radius: 6px; padding: 10px 14px; color: #E5E4E2; font-size: 14px; } QComboBox::drop-down { border: none; width: 30px; } QComboBox::down-arrow { image: none; } QComboBox QAbstractItemView { background-color: #242124; border: 1px solid #555555; selection-background-color: #555555; selection-color: #FFBA00; color: #E5E4E2; border-radius: 6px; padding: 6px; outline: none; }")
        self.mic_combo.wheelEvent = lambda event: event.ignore()
        
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
        lang_label = QLabel("Idioma")
        lang_label.setStyleSheet("color: #E5E4E2; font-size: 14px; background: transparent; border: none; font-weight: bold;")
        lang_label.setFixedWidth(115)
        self.lang_combo = QComboBox()
        self.lang_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_combo.setFixedWidth(330)
        self.lang_combo.setStyleSheet("QComboBox { background-color: #242124; border: none; border-radius: 6px; padding: 10px 14px; color: #E5E4E2; font-size: 14px; } QComboBox::drop-down { border: none; width: 30px; } QComboBox::down-arrow { image: none; } QComboBox QAbstractItemView { background-color: #242124; border: 1px solid #555555; selection-background-color: #555555; selection-color: #FFBA00; color: #E5E4E2; border-radius: 6px; padding: 6px; outline: none; }")
        self.lang_combo.wheelEvent = lambda event: event.ignore()
        
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
        self.format_checkbox = QCheckBox("Aplicar formateo inteligente (Listas y puntuación)")
        self.format_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.format_checkbox.setStyleSheet("QCheckBox { color: #E5E4E2; font-size: 14px; background: transparent; border: none; } QCheckBox::indicator { width: 18px; height: 18px; border: none; border-radius: 4px; background: #242124; } QCheckBox::indicator:checked { background: #FFBA00; }")
        
        smart_formatting_env = os.getenv("SMART_FORMATTING", "False").lower() == "true"
        self.format_checkbox.setChecked(smart_formatting_env)
        self.format_checkbox.stateChanged.connect(self.change_formatting_state)
        
        format_layout.addWidget(self.format_checkbox)
        format_layout.addStretch()
        config_layout.addLayout(format_layout)
        
        # Autostart Selector (Fase 6)
        auto_layout = QHBoxLayout()
        auto_layout.setContentsMargins(0, 5, 0, 0)
        self.auto_checkbox = QCheckBox("Iniciar Vexto automáticamente con Windows")
        self.auto_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auto_checkbox.setStyleSheet("QCheckBox { color: #E5E4E2; font-size: 14px; background: transparent; border: none; } QCheckBox::indicator { width: 18px; height: 18px; border: none; border-radius: 4px; background: #242124; } QCheckBox::indicator:checked { background: #FFBA00; }")
        
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
        self.config_frame.setVisible(False)

        # --- COMPORTAMIENTO DINÁMICO DE ALTURA ---
        # Cuando se despliega o colapsa el layout, forzamos a Qt a recalcular 
        # sin estirar agresivamente los espacios vacíos
        main_layout.addStretch()

        # --- HISTORY SECTION ---
        hist_header_layout = QHBoxLayout()
        hist_header_layout.setContentsMargins(4, 2, 4, 0)
        hist_title = QLabel("Historial de Actividad")
        hist_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #E5E4E2; background: transparent; text-transform: uppercase; letter-spacing: 1.5px;")
        hist_header_layout.addWidget(hist_title)
        
        clear_hist_btn = QPushButton("Limpiar")
        clear_hist_btn.setStyleSheet("QPushButton { background-color: transparent; color: #FFBA00; border: none; font-size: 13px; font-weight: bold; text-decoration: underline; } QPushButton:hover { color: #E5E4E2; }")
        clear_hist_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_hist_btn.setMaximumWidth(80)
        clear_hist_btn.clicked.connect(self.clear_history)
        hist_header_layout.addWidget(clear_hist_btn)
        
        hist_wrapper_layout = QVBoxLayout()
        hist_wrapper_layout.setSpacing(0)
        hist_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        hist_wrapper_layout.addLayout(hist_header_layout)
        
        # Scroll Area for history
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # remove inline style as global style takes over
        
        self.history_container = QWidget()
        self.history_container.setStyleSheet("background-color: #242124;")
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.history_layout.setSpacing(10)
        self.history_layout.setContentsMargins(12, 0, 12, 12)
        
        self.scroll_area.setWidget(self.history_container)
        hist_wrapper_layout.addWidget(self.scroll_area)
        
        # Ocupará un porcentaje relativo pero no forzará límites
        self.scroll_area.setMinimumHeight(150)
        
        main_layout.addLayout(hist_wrapper_layout)

        # Load initial history
        self.refresh_history_ui()

        # Master scroll area for the entire window
        master_scroll = QScrollArea()
        master_scroll.setWidgetResizable(True)
        master_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        master_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        master_widget = QWidget()
        master_widget.setStyleSheet("background-color: transparent;")
        master_widget.setLayout(main_layout)
        
        master_scroll.setWidget(master_widget)
        
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(master_scroll)
        
        # Ejecutar centrado inercial
        self.center_window()
        
    def center_window(self):
        # Mueve la interfaz al centro geométrico del monitor primario
        try:
            screen = QApplication.primaryScreen().availableGeometry().center()
            frame_geometry = self.frameGeometry()
            frame_geometry.moveCenter(screen)
            self.move(frame_geometry.topLeft())
        except:
            pass

    def on_new_dictation(self, text):
        """Called automatically via signal when a new dictation finishes"""
        if text.strip():
            self.history_manager.add_entry(text)
            self.refresh_history_ui()
            
            # Update dashboard metrics
            words_in_text = len(text.split())
            self.total_dictations += 1
            
            today_idx = datetime.now().date()
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            if self.last_dictation_date != today_str:
                if self.last_dictation_date:
                    try:
                        last_dt = datetime.strptime(self.last_dictation_date, "%Y-%m-%d").date()
                        diff = (today_idx - last_dt).days
                        if diff == 1:
                            self.daily_streak += 1
                        elif diff > 1:
                            self.daily_streak = 1
                    except:
                        self.daily_streak = 1
                else:
                    self.daily_streak = 1
                    
                self.last_dictation_date = today_str
                set_key(self.env_path, "LAST_DICTATION_DATE", self.last_dictation_date)
                os.environ["LAST_DICTATION_DATE"] = self.last_dictation_date
                set_key(self.env_path, "DAILY_STREAK", str(self.daily_streak))
                os.environ["DAILY_STREAK"] = str(self.daily_streak)
                
            if words_in_text > 0:
                self.dictated_words += words_in_text
                set_key(self.env_path, "DICTATED_WORDS", str(self.dictated_words))
                os.environ["DICTATED_WORDS"] = str(self.dictated_words)
                
            set_key(self.env_path, "TOTAL_DICTATIONS", str(self.total_dictations))
            os.environ["TOTAL_DICTATIONS"] = str(self.total_dictations)
            
            # Update labels visually
            self.lbl_streak.setText(f"{self.daily_streak} día{'s' if self.daily_streak != 1 else ''} 🔥")
            
            minutes = max(0.0, (self.dictated_words / 40.0) - (self.dictated_words / 150.0))
            time_str = f"{int(minutes)} min" if minutes < 60 else f"{minutes/60:.1f} hrs"
            self.lbl_time.setText(time_str)
            self.lbl_words.setText(f"{self.dictated_words:,}")
        
        w_key = os.environ.get("VEXTO_WHISPER_KEY", "1")
        l_key = os.environ.get("VEXTO_LLAMA_KEY", "1")
        
        def update_dot_color(lbl, target_num, current_key):
            color = "#FFBA00" if current_key == target_num else "#D32F2F" if (target_num == "1" and current_key in ["2", "ERROR"]) or current_key == "ERROR" else "#E5E4E2"
            lbl.setStyleSheet(f"font-size: 16px; background: transparent; color: {color};")
            
        update_dot_color(self.dot_w1, "1", w_key)
        update_dot_color(self.dot_w2, "2", w_key)
        update_dot_color(self.dot_l1, "1", l_key)
        update_dot_color(self.dot_l2, "2", l_key)
        self.lbl_dicts.setText(f"{self.total_dictations:,}")

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
            empty_lbl.setStyleSheet("color: #E5E4E2; font-style: italic; font-size: 14px; background: transparent; opacity: 0.7;")
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
                mt = "0px" if not current_date_group else "24px"
                header.setStyleSheet(f"font-weight: bold; color: #E5E4E2; margin-top: {mt}; margin-bottom: 8px; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; background: transparent;")
                self.history_layout.addWidget(header)
                
            # Add Item
            self._add_history_item_widget(entry)

    def _add_history_item_widget(self, entry):
        item_frame = QFrame()
        item_frame.setStyleSheet("QFrame { background-color: #555555; border: none; border-radius: 8px; }")
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(18, 16, 18, 16)
        item_layout.setSpacing(10)
        
        # Time and Copy Row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0,0,0,0)
        
        time_lbl = QLabel(f"{entry.get('time', '')}")
        time_lbl.setStyleSheet("color: #E5E4E2; font-size: 12px; border: none; background: transparent; opacity: 0.6;")
        top_row.addWidget(time_lbl)
        top_row.addStretch()
        
        copy_btn = QPushButton("Copiar")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("QPushButton { background-color: transparent; color: #FFBA00; border: none; padding: 0; font-size: 12px; font-weight: bold; text-decoration: underline; } QPushButton:hover { color: #E5E4E2; }")
        
        # Inline function to handle copy
        def make_copy_func(text_to_copy):
            def copy_to_clipboard():
                QApplication.clipboard().setText(text_to_copy)
                copy_btn.setText("✓ Copiado")
                copy_btn.setStyleSheet("QPushButton { background-color: transparent; color: #E5E4E2; border: none; padding: 0; font-size: 12px; font-weight: bold; }")
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

    def toggle_config_section(self):
        is_visible = self.config_frame.isVisible()
        self.config_frame.setVisible(not is_visible)
        if is_visible:
            self.config_title_btn.setText("▶ Configuración General")
        else:
            self.config_title_btn.setText("▼ Configuración General")

    def clear_history(self):
        reply = QMessageBox.question(self, "Limpiar Historial", 
                                     "¿Estás seguro de que deseas borrar todos tus dictados guardados? Esta acción no se puede deshacer y tu contador global regresará a cero.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear()
            self.refresh_history_ui()
            
            # Reset word counter and all dashboard metrics
            self.dictated_words = 0
            self.total_dictations = 0
            self.daily_streak = 0
            self.last_dictation_date = ""
            
            self.lbl_streak.setText("0 días 🔥")
            self.lbl_time.setText("0 min")
            self.lbl_words.setText("0")
            self.lbl_dicts.setText("0")
            
            set_key(self.env_path, "DICTATED_WORDS", "0")
            set_key(self.env_path, "TOTAL_DICTATIONS", "0")
            set_key(self.env_path, "DAILY_STREAK", "0")
            set_key(self.env_path, "LAST_DICTATION_DATE", "")
            
            os.environ["DICTATED_WORDS"] = "0"
            os.environ["TOTAL_DICTATIONS"] = "0"
            os.environ["DAILY_STREAK"] = "0"
            os.environ["LAST_DICTATION_DATE"] = ""



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

    def setup_tray(self):
        # Usamos el logo oficial para el System Tray
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo3.svg")
        icon = QIcon(icon_path)
        self.tray_icon = QSystemTrayIcon(icon, self)
        
        self.tray_icon.setToolTip("Vexto Dictation - En espera")
        
        # Crear menu nativo
        tray_menu = QMenu(self)
        
        config_action = QAction("⚙️ Abrir Configuración", self)
        config_action.triggered.connect(self.show_window)
        tray_menu.addAction(config_action)
        
        quit_action = QAction("❌ Salir de Vexto", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # Conectar el doble clic izquierdo
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()
            
    def show_window(self):
        self.show()
        self.activateWindow()
        self.raise_()
        
    def quit_app(self):
        print("Cerrando Vexto por completo...")
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        self.tray_icon.hide()
        QApplication.quit()
        # Matamos abruptamente el proceso para evitar hilos zombis (Ej. del módulo keyboard)
        import os
        os._exit(0)

    def closeEvent(self, event):
        # En lugar de cerrar la app o los servicios, solo ocultamos la ventana visual
        self.hide()
        event.ignore()

def main():
    import ctypes
    try:
        myappid = 'vexto.dictation.app.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Set Global App Icon (Taskbar)
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo3.svg")
    app.setWindowIcon(QIcon(icon_path))
    
    window = ControlPanelWindow()
    
    # Mostrar la ventana SOLO si el usuario no tiene la API Key
    if not (os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "tu_clave_aqui"):
        window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
