from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QColor, QPainter, QFont, QPen
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QTextDocument

import sys


class SquareWidget(QWidget):
    instances = []

    def __init__(self, x=100, y=100, width=100, height=None, color="red", parent=None,
                 font_size=14, text="", text_color="white", show_on_init=True, auto_font_resize=False):
        """
        Crea un widget rectangular/cuadrado personalizable.

        Parámetros:
        - x, y: posición inicial del widget.
        - width, height: dimensiones del rectángulo (si height es None, usa width -> cuadrado).
        - color: color de fondo.
        - font_size: tamaño inicial de la fuente del texto.
        - text: texto a mostrar.
        - text_color: color del texto.
        - auto_font_resize: ajusta automáticamente el tamaño de la fuente según el tamaño del widget.
        """
        super().__init__(parent)

        # --- Atributos de forma ---
        self.width = width
        self.height = height if height is not None else width
        self.square_color = QColor(color)

        # --- Atributos de texto ---
        self.text = text
        self.text_color = QColor(text_color)
        self.font_size = font_size
        self.auto_font_resize = auto_font_resize

        # --- Estado interno ---
        self.active = True
        self.dragging = False
        self.offset = QPoint()

        # --- Configuración visual ---
        self.setGeometry(x, y, self.width, self.height)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if show_on_init:
            self.show()

        SquareWidget.instances.append(self)

    def paintEvent(self, event):
        """
        Maneja el evento de pintura del widget.
        Además dibuja un cuadrado y texto centrado en el widget.
        Params:
        - event (QEvent): El evento de pintura

        NOTA: Según la documentación de PyQt, esta función es llamada automáticamente por el sistema
        cuando el widget necesita ser redibujado. NO se debe llamar manualmente.
        link: https://doc.qt.io/qt-6/qwidget.html#paintEvent
        """
        if not self.active:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Dibuja fondo
        painter.setBrush(self.square_color)
        painter.setPen(Qt.black)
        painter.drawRect(0, 0, self.width, self.height)

        # Calcula tamaño de fuente (si auto-ajuste activado)
        font_size = self._calculate_font_size() if self.auto_font_resize else self.font_size
        font = QFont("Arial", font_size)
        painter.setFont(font)
        painter.setPen(QPen(self.text_color))

        # Dibuja texto html
        doc = QTextDocument()
        doc.setHtml(self.text)
        doc.setTextWidth(self.width)
        painter.translate(0, (self.height - doc.size().height()) / 2)
        doc.drawContents(painter)

    def change_text(self, text):
        """Cambia el texto mostrado."""
        self.text = text
        self.update()

    def change_text_color(self, color):
        """Cambia el color del texto."""
        self.text_color = QColor(color)
        self.update()

    def change_font_size(self, size):
        """Cambia el tamaño de la fuente del texto."""
        self.font_size = size
        self.update()

    # Alias más legibles
    def set_font_size(self, size):
        """Setter alternativo del tamaño de fuente."""
        self.change_font_size(size)

    def get_font_size(self):
        """Devuelve el tamaño actual de la fuente."""
        return self.font_size

    def enable_auto_font_resize(self, enable=True):
        """Activa o desactiva el ajuste automático de tamaño de fuente."""
        self.auto_font_resize = enable
        self.update()

    def _calculate_font_size(self):
        """Calcula automáticamente un tamaño de fuente proporcional al widget."""
        base = min(self.width, self.height)
        return max(8, int(base * 0.15))  # 15% del tamaño del lado menor

    def change_color(self, color):
        self.square_color = QColor(color)
        self.update()

    def resize_rectangle(self, new_width, new_height):
        """Cambia el tamaño del rectángulo y actualiza."""
        self.width = new_width
        self.height = new_height
        self.setFixedSize(new_width, new_height)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.active:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging and self.active:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def activate(self):
        self.active = True
        self.show()
        self.update()

    def deactivate(self):
        self.active = False
        self.hide()

    def move_to(self, x, y):
        self.move(x, y)

    def closeEvent(self, event):
        if self in SquareWidget.instances:
            SquareWidget.instances.remove(self)
        super().closeEvent(event)

    @classmethod
    def close_all(cls):
        for inst in cls.instances[:]:
            inst.close()
        cls.instances.clear()
