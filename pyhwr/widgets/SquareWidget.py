from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QColor, QPainter, QFont, QPen
from PyQt5.QtCore import Qt, QPoint
import sys

class SquareWidget(QWidget):

    instances = []

    def __init__(self, x=100, y=100, size=100, color="red", parent=None,
                 font_size=14, text="", text_color="white", show_on_init=True):
        """
        Crea un widget cuadrado que puede ser arrastrado y personalizado.
        Params:
        - x (int): Posición X inicial del cuadrado.
        - y (int): Posición Y inicial del cuadrado.
        - size (int): Tamaño del cuadrado.
        - color (str): Color del cuadrado en formato hexadecimal o nombre de color.
        - parent (QWidget): Widget padre al que se adjunta este cuadrado.
        - font_size (int): Tamaño de la fuente del texto dentro del cuadrado.
        - text (str): Texto a mostrar dentro del cuadrado.
        - text_color (str): Color del texto en formato hexadecimal o nombre de color.
        - show_on_init (bool): Si se debe mostrar el cuadrado al inicializar.
        """
        super().__init__(parent)
        self.size = size
        self.square_color = QColor(color)
        self.text = text
        self.text_color = QColor(text_color)
        self.font_size = font_size
        self.active = True
        self.dragging = False
        self.offset = QPoint()

        self.setGeometry(x, y, size, size)
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

        #Dibujamos el cuadrado
        painter.setBrush(self.square_color)
        painter.setPen(Qt.black)
        painter.drawRect(0, 0, self.size, self.size)

        #Dibujamos el texto centrado
        painter.setPen(QPen(self.text_color))
        font = QFont("Arial", self.font_size)
        painter.setFont(font)
        rect = self.rect()
        painter.drawText(rect, Qt.AlignCenter, self.text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.active:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging and self.active:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.dragging = False

    ## Métodos para cambiar propiedades del widget
    ## Estos métodos actualizan el color, texto, color del texto, tamaño de fuente, etc.
    def change_color(self, color):
        """ Cambia el color del cuadrado.
        Params:
        - color (str): Nuevo color del cuadrado en formato hexadecimal o nombre de color.
        """
        self.square_color = QColor(color)
        self.update()

    def change_text(self, text):
        """ Cambia el texto dentro del cuadrado.
        Params:
        - text (str): Nuevo texto a mostrar dentro del cuadrado.
        """
        self.text = text
        self.update()

    def change_text_color(self, color):
        """ Cambia el color del texto dentro del cuadrado.
        Params:
        - color (str): Nuevo color del texto en formato hexadecimal o nombre de color.
        """
        self.text_color = QColor(color)
        self.update()

    def change_font_size(self, size):
        """ Cambia el tamaño de la fuente del texto dentro del cuadrado.
        Params:
        - size (int): Nuevo tamaño de la fuente.
        """
        self.font_size = size
        self.update()

    def activate(self):
        """
        Activa el widget, mostrándolo y permitiendo que responda a eventos."""
        self.active = True
        self.show()
        self.update()

    def deactivate(self):
        """
        Desactiva el widget, ocultándolo y evitando que responda a eventos."""
        self.active = False
        self.hide()

    def move_to(self, x, y):
        """
        Mueve el widget a una nueva posición (x, y)."""
        self.move(x, y)

    def resize_square(self, new_size):
        """
        Cambia el tamaño del cuadrado y actualiza su geometría."""
        self.size = new_size
        self.setFixedSize(new_size, new_size)
        self.update()

    def closeEvent(self, event):
        """
        Maneja el evento de cierre del widget."""
        if self in SquareWidget.instances:
            SquareWidget.instances.remove(self)
        super().closeEvent(event)

    @classmethod
    def close_all(cls):
        """
        Cierra todos los widgets de tipo SquareWidget.
        """
        for inst in cls.instances[:]:
            inst.close()
        ##eliminar la lista de instancias
        cls.instances.clear()

def cambiar_color_widget(widget, color: str):
    widget.change_color(color)

if __name__ == "__main__":
    from PyQt5.QtCore import QTimer
    from functools import partial
    # Si ya hay una instancia de QApplication, usala
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    marcador1 = SquareWidget(x=200, y=200, size=150, color="black",
                             text="Marcador 1", text_color="white")
    marcador2 = SquareWidget(x=500, y=200, size=150, color="white",
                             text="Marcador 2", text_color="black")

    cambiar_marc1 = partial(cambiar_color_widget, marcador1, color="#15945D")
    cambiar_marc2 = partial(cambiar_color_widget, marcador2, color="#FF5733")

    QTimer.singleShot(2000, cambiar_marc1)
    QTimer.singleShot(2000, cambiar_marc2)

    marcador1.change_color("#281818")
    # marcador1.resize_square(200)
    # marcador1.change_text("Mark 2")

    QTimer.singleShot(4000, SquareWidget.close_all)