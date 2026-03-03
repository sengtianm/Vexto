import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QMessageBox,
                             QScrollArea, QFrame, QInputDialog, QComboBox, QCheckBox,
                             QSystemTrayIcon, QMenu, QGridLayout)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal
from src.utils import HISTORY_FILE, ENV_FILE, LOGO_ICON
from src.utils import ConfigKeys, EnvVars, AppState

from src.services import HistoryManager
from src.services import DashboardMetricsService
from src.services import AppSettingsService

class ControlPanelWindow(QWidget):
    # Definir señal para poder agregar texto al historial desde el hilo secundario
    add_history_signal = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.env_path = ENV_FILE
        # Load existing or create empty
        if not os.path.exists(self.env_path):
            with open(self.env_path, 'w') as f:
                f.write(f"{ConfigKeys.GROQ_API_KEY}=\n{ConfigKeys.RECORD_HOTKEY}=ctrl+space\n")
        load_dotenv(self.env_path)
        
        self.history_manager = HistoryManager()
        self.dashboard_service = DashboardMetricsService()
        self.app_settings = AppSettingsService()
        self.hotkey_manager = None
        
        # Connect signal
        self.add_history_signal.connect(self.on_new_dictation)
        
        self.init_ui()
        self.setup_tray()
        
        # Iniciar backend automáticamente si hay clave
        if os.getenv(ConfigKeys.GROQ_API_KEY) and os.getenv(ConfigKeys.GROQ_API_KEY) != "tu_clave_aqui":
            self.start_backend()

    def init_ui(self) -> None:
        self.setWindowTitle("Vexto - Panel de Control")
        # Diseño base cuadrado (Square UI), desbloqueando el límite vertical para manipulación del usuario
        self.setMinimumSize(540, 460)
        self.resize(560, 580)
        
        # Cargar CSS Global Refactorizado
        from src.utils import PROJECT_ROOT
        style_path = os.path.join(PROJECT_ROOT, "src", "assets", "styles.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(35, 35, 35, 35)
        main_layout.setSpacing(12)
        
        # --- HEADER ---
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.setContentsMargins(4, 0, 0, 0)
        
        title = QLabel("Vexto")
        title.setObjectName("AppTitle")
        
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
            card.setProperty("cssClass", "StatCard")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 12, 15, 12)
            c_layout.setSpacing(2)
            
            lbl_title = QLabel(title.upper())
            lbl_title.setProperty("cssClass", "StatCardTitle")
            
            lbl_val = QLabel(value)
            lbl_val.setProperty("cssClass", "StatCardValueStreak" if val_color == "#FFBA00" else "StatCardValueNormal")
            
            lbl_sub = QLabel(subtitle)
            lbl_sub.setWordWrap(True)
            lbl_sub.setProperty("cssClass", "StatCardSub")
            
            c_layout.addWidget(lbl_title)
            c_layout.addWidget(lbl_val)
            c_layout.addWidget(lbl_sub)
            return card, lbl_val, lbl_sub
            
        stats = self.dashboard_service
        self.card_streak, self.lbl_streak, _ = create_stat_card("Racha Diaria", f"{stats.daily_streak} día{'s' if stats.daily_streak != 1 else ''} 🔥", "¡Sigue así!", "#FFBA00")
        self.card_time, self.lbl_time, _ = create_stat_card("Tiempo Ahorrado", stats.get_time_saved_str(), "Neto vs Manual")
        self.card_words, self.lbl_words, _ = create_stat_card("Palabras", f"{stats.dictated_words:,}", "Dictadas en total")
        self.card_dicts, self.lbl_dicts, _ = create_stat_card("Dictados", f"{stats.total_dictations:,}", "Disparos totales")
        
        dashboard_layout.addWidget(self.card_streak, 0, 0)
        dashboard_layout.addWidget(self.card_time, 0, 1)
        dashboard_layout.addWidget(self.card_words, 1, 0)
        dashboard_layout.addWidget(self.card_dicts, 1, 1)
        
        # --- HORIZONTAL AI MONITOR ---
        self.monitor_card = QFrame()
        self.monitor_card.setProperty("cssClass", "StatCard")
        
        self.monitor_layout = QHBoxLayout(self.monitor_card)
        self.monitor_layout.setContentsMargins(15, 8, 15, 8)
        self.monitor_layout.setSpacing(15)
        self.monitor_layout.addStretch()
        
        def update_dot_color(lbl, target_num, current_key):
            err = EnvVars.ERROR_VAL
            color = "#FFBA00" if current_key == target_num else "#D32F2F" if (target_num == "1" and current_key in ["2", err]) or current_key == err else "#E5E4E2"
            lbl.setStyleSheet(f"font-size: 24px; background: transparent; color: {color};")
            
        def create_indicator(text):
            h_layout = QHBoxLayout()
            h_layout.setSpacing(4)
            h_layout.setContentsMargins(0, 0, 0, 0)
            
            lbl_txt = QLabel(text)
            lbl_txt.setProperty("cssClass", "MonitorIndicatorText")
            lbl_txt.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            
            lbl_dot = QLabel("●")
            lbl_dot.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            
            h_layout.addWidget(lbl_txt)
            h_layout.addWidget(lbl_dot)
            self.monitor_layout.addLayout(h_layout)
            return lbl_dot
            
        self.dot_w1 = create_indicator("Whisper (L1)")
        self.dot_w2 = create_indicator("Whisper (L2)")
        self.dot_l1 = create_indicator("Llama 3.3 (L1)")
        self.dot_l2 = create_indicator("Llama 3.3 (L2)")
        
        w_key = os.environ.get(EnvVars.WHISPER_KEY, "1")
        l_key = os.environ.get(EnvVars.LLAMA_KEY, "1")
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
        self.config_title_btn.setProperty("cssClass", "ConfigSectionTitle")
        self.config_title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_title_btn.clicked.connect(self.toggle_config_section)
        
        config_header_layout.addWidget(self.config_title_btn)
        config_header_layout.addStretch()
        
        main_layout.addLayout(config_header_layout)
        
        self.config_frame = QFrame()
        config_frame = self.config_frame
        config_frame.setObjectName("ConfigFrame")
        config_layout = QVBoxLayout(config_frame)
        config_layout.setContentsMargins(20, 24, 20, 24)
        config_layout.setSpacing(16)
        
        # Hotkey Info
        hotq_layout = QHBoxLayout()
        hotq_label = QLabel("Atajo de Dictado")
        hotq_label.setProperty("cssClass", "ConfigLabel")
        hotq_label.setFixedWidth(115)
        hotq_val = self.app_settings.get(ConfigKeys.RECORD_HOTKEY)
        self.hotq_display = QLabel(f"{hotq_val.upper()}")
        self.hotq_display.setProperty("cssClass", "HotkeyDisplay")
        
        edit_hotq_btn = QPushButton("Cambiar Atajo")
        edit_hotq_btn.setProperty("cssClass", "LinkButton")
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
        mic_label.setProperty("cssClass", "ConfigLabel")
        mic_label.setFixedWidth(115)
        self.mic_combo = QComboBox()
        self.mic_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_combo.setFixedWidth(330)
        self.mic_combo.wheelEvent = lambda event: event.ignore() # type: ignore
        
        # Populate Mics
        from src.audio import AudioRecorder
        self.mics_list = AudioRecorder.get_microphones()
        
        current_mic_idx_str = self.app_settings.get(ConfigKeys.RECORD_DEVICE_INDEX)
        current_mic_idx = int(current_mic_idx_str) if current_mic_idx_str and current_mic_idx_str.isdigit() else None
        
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
        self.lang_combo.wheelEvent = lambda event: event.ignore() # type: ignore
        
        self.lang_combo.addItem("Español", "es")
        self.lang_combo.addItem("Inglés", "en")
        
        current_lang = self.app_settings.get(ConfigKeys.RECORD_LANGUAGE)
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
        self.format_checkbox.setProperty("cssClass", "ConfigCheckBox")
        self.format_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        
        smart_formatting_env = self.app_settings.get(ConfigKeys.SMART_FORMATTING).lower() == "true"
        self.format_checkbox.setChecked(smart_formatting_env)
        self.format_checkbox.stateChanged.connect(self.change_formatting_state)
        
        format_layout.addWidget(self.format_checkbox)
        format_layout.addStretch()
        config_layout.addLayout(format_layout)
        
        # Autostart Selector (Fase 6)
        auto_layout = QHBoxLayout()
        auto_layout.setContentsMargins(0, 5, 0, 0)
        self.auto_checkbox = QCheckBox("Iniciar Vexto automáticamente con Windows")
        self.auto_checkbox.setProperty("cssClass", "ConfigCheckBox")
        self.auto_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Leemos el estado real del registro por seguridad, o el .env
        import src.utils.autostart as autostart
        is_auto = autostart.is_autostart_enabled()
        # Reparamos el setting json si no coincide
        self.app_settings.set(ConfigKeys.AUTOSTART, "True" if is_auto else "False")
        
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
        # Top margin increased (yellow line), bottom margin decreased (green line)
        hist_header_layout.setContentsMargins(4, 32, 4, 8)
        hist_title = QLabel("Historial de Actividad")
        hist_title.setProperty("cssClass", "SectionHeader")
        hist_header_layout.addWidget(hist_title)
        
        clear_hist_btn = QPushButton("Limpiar")
        clear_hist_btn.setProperty("cssClass", "LinkButton")
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
        self.history_container.setProperty("cssClass", "HistoryContainer")
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
        master_scroll.setObjectName("MasterScroll")
        master_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        master_widget = QWidget()
        master_widget.setObjectName("MasterWidget")
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
            
            # Update metrics via Service
            self.dashboard_service.add_dictation(text)
            
            # Update labels visually
            stats = self.dashboard_service
            self.lbl_streak.setText(f"{stats.daily_streak} día{'s' if stats.daily_streak != 1 else ''} 🔥")
            self.lbl_time.setText(stats.get_time_saved_str())
            self.lbl_words.setText(f"{stats.dictated_words:,}")
            self.lbl_dicts.setText(f"{stats.total_dictations:,}")
        
        w_key = os.environ.get(EnvVars.WHISPER_KEY, "1")
        l_key = os.environ.get(EnvVars.LLAMA_KEY, "1")
        
        def update_dot_color(lbl, target_num, current_key):
            err = EnvVars.ERROR_VAL
            color = "#FFBA00" if current_key == target_num else "#D32F2F" if (target_num == "1" and current_key in ["2", err]) or current_key == err else "#E5E4E2"
            lbl.setStyleSheet(f"font-size: 16px; background: transparent; color: {color};")
            
        update_dot_color(self.dot_w1, "1", w_key)
        update_dot_color(self.dot_w2, "2", w_key)
        update_dot_color(self.dot_l1, "1", l_key)
        update_dot_color(self.dot_l2, "2", l_key)
        stats = self.dashboard_service
        self.lbl_dicts.setText(f"{stats.total_dictations:,}")

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
            empty_lbl.setProperty("cssClass", "HistoryEmpty")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_layout.addWidget(empty_lbl)
            return

        # Group by Date
        current_date_group = None
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        for entry in entries:
            # Parse timestamp to date and time if missing
            ts = entry.get("timestamp")
            if ts and not entry.get("time"):
                try:
                    dt = datetime.fromisoformat(ts)
                    entry["date"] = dt.strftime("%Y-%m-%d")
                    entry["time"] = dt.strftime("%I:%M %p").lower()
                except Exception:
                    entry["date"] = "Hoy"
                    entry["time"] = "--:--"
                    
            date_str = entry.get("date")
            
            # Add Header if date changed
            if date_str != current_date_group:
                current_date_group = date_str
                
                header = QLabel("Hoy" if date_str == today_str else date_str)
                mt = "0px" if not current_date_group else "24px"
                header.setProperty("cssClass", "HistoryDateHeader")
                header.setStyleSheet(f"margin-top: {mt};")
                self.history_layout.addWidget(header)
                
            # Add Item
            self._add_history_item_widget(entry)

    def _add_history_item_widget(self, entry):
        item_frame = QFrame()
        item_frame.setProperty("cssClass", "HistoryItemFrame")
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(18, 16, 18, 16)
        item_layout.setSpacing(10)
        
        # Time and Copy Row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0,0,0,0)
        
        time_lbl = QLabel(f"{entry.get('time', '')}")
        time_lbl.setProperty("cssClass", "HistoryItemTime")
        top_row.addWidget(time_lbl)
        top_row.addStretch()
        
        copy_btn = QPushButton("Copiar")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setProperty("cssClass", "HistoryItemCopy")
        
        # Inline function to handle copy
        def make_copy_func(text_to_copy):
            def copy_to_clipboard():
                QApplication.clipboard().setText(text_to_copy)
                copy_btn.setText("✓ Copiado")
                copy_btn.setStyleSheet("color: #E5E4E2; text-decoration: none;")
            return copy_to_clipboard
            
        copy_btn.clicked.connect(make_copy_func(entry.get("text", "")))
        top_row.addWidget(copy_btn)
        
        item_layout.addLayout(top_row)
        
        # Text Content
        text_disp = QLabel(entry.get("text", ""))
        text_disp.setWordWrap(True)
        text_disp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_disp.setProperty("cssClass", "HistoryItemText")
        
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
            self.dashboard_service.reset_stats()
            
            self.lbl_streak.setText("0 días 🔥")
            self.lbl_time.setText("0 min")
            self.lbl_words.setText("0")
            self.lbl_dicts.setText("0")



    def change_hotkey(self):
        current = self.app_settings.get(ConfigKeys.RECORD_HOTKEY)
        text, ok = QInputDialog.getText(self, 'Cambiar Atajo', 
            'Ingresa el nuevo atajo:\n(Ejemplos: ctrl+space, alt+x, ctrl+shift+a)',
            QLineEdit.EchoMode.Normal, current)
            
        if ok and text.strip():
            new_hotkey = text.strip().lower()
            # 1. Update UI
            self.hotq_display.setText(new_hotkey.upper())
            # 2. Update config file (aislado)
            self.app_settings.set(ConfigKeys.RECORD_HOTKEY, new_hotkey)
            # 3. Reload backend if active
            if self.hotkey_manager:
                print(f"Reiniciando backend con nuevo atajo: {new_hotkey}")
                self.start_backend()

    def change_microphone(self, index):
        mic_id_data = self.mic_combo.itemData(index)
        
        if mic_id_data == -1: 
            # Predeterminado
            self.app_settings.set(ConfigKeys.RECORD_DEVICE_INDEX, "")
            print("Micrófono cambiado a: Predeterminado")
        else:
            # Especifico
            self.app_settings.set(ConfigKeys.RECORD_DEVICE_INDEX, str(mic_id_data))
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
        self.app_settings.set(ConfigKeys.RECORD_LANGUAGE, lang_data)
        
        print(f"Idioma cambiado a: {lang_data}")
        # En el caso del idioma, ni siquiera hace falta reiniciar el Thread entero,
        # pero reiniciar asegura un estado limpio de todo.
        if self.hotkey_manager:
            self.start_backend()
            
        self.lang_combo.blockSignals(False)

    def change_formatting_state(self, state):
        is_checked = bool(state == Qt.CheckState.Checked.value or state == 2)
        val_str = "True" if is_checked else "False"
        self.app_settings.set(ConfigKeys.SMART_FORMATTING, val_str)
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
        self.app_settings.set(ConfigKeys.AUTOSTART, val_str)
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
        icon = QIcon(LOGO_ICON)
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
        self.tray_icon.hide()
        
        # Ocultar la ventana de inmediato para responsividad
        self.hide()
        
        # Invocamos el apagado elegante de hilos
        try:
            from main import stop_background_services
            stop_background_services(self.hotkey_manager)
        except Exception as e:
            print(f"Error durante el apagado elegante: {e}")
            
        QApplication.quit()

    def closeEvent(self, event):
        # En lugar de cerrar la app o los servicios, solo ocultamos la ventana visual
        self.hide()
        event.ignore()

def main():
    import ctypes
    try:
        myappid = 'vexto.dictation.app.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"Falla silenciosa registrando AppUserModelID: {e}")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Set Global App Icon (Taskbar)
    app.setWindowIcon(QIcon(LOGO_ICON))
    
    window = ControlPanelWindow()
    
    # Mostrar la ventana SOLO si el usuario no tiene la API Key
    if not (os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "tu_clave_aqui"):
        window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
