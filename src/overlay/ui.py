import math
from typing import Any
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QRectF
from src.utils import AppState
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush

class OverlaySignals(QObject):
    # Signals are thread-safe in PyQt!
    update_state = pyqtSignal(str)
    update_volume = pyqtSignal(float)

class VextoOverlay(QWidget):
    """Modern Dynamic Pill interface for Vexto."""
    def __init__(self) -> None:
        super().__init__()
        self.signals = OverlaySignals()
        self.signals.update_state.connect(self.set_state)
        self.signals.update_volume.connect(self.set_volume)
        self.current_state = AppState.IDLE
        self.current_volume = 0.0
        
        # Animation variables
        self.anim_tick = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        
        self.init_ui()

    def init_ui(self) -> None:
        # Frameless, Always on Top, and Tool (hides from Windows taskbar)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Dimensiones de la Píldora (Basada en la imagen: ancha y compacta)
        self.target_width = 70
        self.target_height = 26
        self.resize(self.target_width, self.target_height)
        
        # Se calculará la posición dinámicamente cada vez que se muestre
        self.hide()

    def update_position(self) -> None:
        """Mueve la píldora al centro superior del monitor activo (donde esté el mouse)"""
        # Obtener la posición global del mouse
        cursor_pos = self.cursor().pos()
        
        # Encontrar qué pantalla contiene ese mouse
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
            
        if screen is not None:
            geom = screen.geometry()
            
            # Centrar horizontalmente en esa pantalla, y colocar a 16px del borde superior
            self.move(int(geom.x() + geom.width() / 2 - self.width() / 2), geom.y() + 16)

    def set_volume(self, vol: float) -> None:
        self.current_volume = vol

    def set_state(self, state: str) -> None:
        self.current_state = state
        self.anim_tick = 0 # reset animation
        self.current_volume = 0.0 # Reset visual memory
        
        if state == AppState.IDLE:
            self.timer.stop()
            self.hide()
        elif state == AppState.LISTENING:
            self.update_position() # Mover al monitor correcto
            self.show()
            self.timer.start(16) # ~60 fps
        elif state == AppState.PROCESSING:
            self.update_position()
            self.show()
            self.timer.start(16)
        elif state == AppState.ERROR:
            self.update_position()
            self.show()
            self.timer.start(16)
            QTimer.singleShot(2500, lambda: self.set_state(AppState.IDLE))

    def animate(self) -> None:
        self.anim_tick += 1
        self.update() # Llama a paintEvent automáticamente

    def paintEvent(self, event: Any) -> None:
        """Dibuja completamente la UI estilo Glassmorphism y sus animaciones con Pincel vectorial."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # == 1. Dibujar el Fondo de la Píldora ==
        rect = QRectF(2, 2, self.width()-4, self.height()-4)
        path = QPainterPath()
        path.addRoundedRect(rect, (self.height()-4) / 2, (self.height()-4) / 2)
        
        # Relleno: Negro oscuro sólido (no transparente)
        painter.fillPath(path, QBrush(QColor(0, 0, 0, 255)))
        
        # Sin borde: Se dibujará solo el fondo oscuro flotante
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        # == 2. Dibujar las Animaciones según el estado ==
        if self.current_state == AppState.LISTENING:
            self._draw_audio_waves(painter)
        elif self.current_state == AppState.PROCESSING:
            self._draw_spinner(painter)
        elif self.current_state == AppState.ERROR:
            self._draw_error(painter)
            
        painter.end()

    def _draw_audio_waves(self, painter: QPainter) -> None:
        """Ondas reactivas al sonido real (Aumentada sensibilidad)"""
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # Puntos base aún más pequeños
        num_bars = 4
        bar_width = 2.5 
        spacing = 4 
        
        total_width = (num_bars * bar_width) + ((num_bars - 1) * spacing)
        start_x = center_x - (total_width / 2)
        
        painter.setPen(Qt.PenStyle.NoPen)
        # Blanco sólido
        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
        
        # Leer el volumen procesado por la señal asíncrona
        vol = self.current_volume
            
        is_silent = vol < 0.02
        
        for i in range(num_bars):
            if is_silent:
                # Si no hay sonido, mostrar puntos suspensivos diminutos
                bar_height = bar_width 
                
                # Respiración
                phase = self.anim_tick * 0.05 + i * 1.5
                alpha = int(120 + 80 * math.sin(phase))
                painter.setBrush(QBrush(QColor(255, 255, 255, alpha)))
                
            else:
                # Hay volumen: Multiplicador gigante para muchísima sensibilidad
                phase = self.anim_tick * 0.2 + i * 1.0
                
                # Multiplicador súper agresivo (x45), topando en 12px 
                reactive_height = vol * 45 
                variation = math.sin(phase) * (reactive_height * 0.4)
                
                # Altura mínima 2.5, altura máxima estética 12
                bar_height = max(bar_width, min(12, reactive_height + variation))
            
            x = start_x + i * (bar_width + spacing)
            y = center_y - (bar_height / 2)
            
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_height), 
                                  int(bar_width/2), int(bar_width/2))
            
    def _draw_spinner(self, painter: QPainter) -> None:
        """Anillo de carga minimalista y elegante pequeño"""
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # Radio delicado y proporcional (4px = 8px diametro total, centra perfecto)
        radius = 4
        
        pen = QPen(QColor(255, 255, 255, 255))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Rotar rápido
        start_angle = (self.anim_tick * 15) % 360
        span_angle = 120 
        
        painter.drawArc(
            int(center_x - radius), 
            int(center_y - radius), 
            int(radius * 2), 
            int(radius * 2), 
            -start_angle * 16, 
            -span_angle * 16
        )

    def _draw_error(self, painter):
        """Cruz visible minimalista de color rojo alerta"""
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        pen = QPen(QColor(239, 68, 68, 255))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        painter.drawLine(int(center_x - 4), int(center_y - 4), int(center_x + 4), int(center_y + 4))
        painter.drawLine(int(center_x + 4), int(center_y - 4), int(center_x - 4), int(center_y + 4))
