from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
import sys
import os
import winsound

class StimuliWindow(QMainWindow):
    """
    Interfaz gráfica que tiene como fin únicamente mostrar la orden para la adquisición de datos 
    de entrenamiento para el clasificador
    """
    def __init__(self, textoInicial = "Preparando experimento..."):
        super().__init__()
        self.setWindowFlags(Qt.Window)
        ui_path = os.path.join(os.path.dirname(__file__), 'StimuliWindow.ui')
        uic.loadUi(ui_path, self)

        self.resize(1200, 800)  # tamaño inicial
        self.setMinimumSize(800, 600)  # opcional

        self.label_orden.setVisible(True)
        self.cruz.setVisible(False)

        self.current_state = "init"

        self.layouts = {
            "init": {
                self.cruz: (0.5, 0.4),
                self.label_orden: (0.5, 0.5),},
            "cruz_centrada":{
                self.cruz: (0.5, 0.5),},
            "cruz_arriba":{
                self.cruz: (0.5, 0.05),},
            "cruz_abajo":{
                self.cruz: (0.5, 0.95),},
            "cruz_izquierda":{
                self.cruz: (0.05, 0.5),},
            "cruz_derecha":{
                self.cruz: (0.95, 0.5),},
            "orden_centrada":{
                self.label_orden: (0.5, 0.5),},
            "orden_arriba_cruz_centrada": {
                self.label_orden: (0.5, 0.44),
                self.cruz: (0.5, 0.5),
            },
                    }
        
        self.widgetsDict = {"label_orden": self.label_orden,
                            "cruz": self.cruz,}
        
        self.update_order(textoInicial)
        self.place_widget("cruz",0.1,0.1)
        self.modo_cue()

    def update_order(self, texto,
                     fontsize = 36,
                     border = "0px",
                     font_color = "#322CAE"):
        """
        Actualiza la etiqueta que da la orden
            texto (str): texto de la orden
        """
        self.label_orden.setFont(QFont('Berlin Sans', fontsize))
        self.label_orden.setText(texto)
        self.label_orden.setStyleSheet(f"border: {border}; color: {font_color};")
    
    def place_widget(self, widget, x_ratio, y_ratio):
        """
        Posiciona un widget en función del tamaño de la ventana
        widget: el widget a posicionar. Puede ser un string con la clave del widget en self.widgetsDict o el widget en sí.
        x_ratio, y_ratio ∈ [0,1]
        """
        if isinstance(widget, str):
            widget = self.widgetsDict[widget]
            
        w = self.centralWidget().width()
        h = self.centralWidget().height()

        widget.move(
            int(w * x_ratio - widget.width() / 2),
            int(h * y_ratio - widget.height() / 2)
        )

    def update_positions(self, widget:str=None):
        """
        Actualiza la posición de los widgets en función del tamaño de la ventana. Si se especifica un widget, solo actualiza ese widget.
        widget: el widget a posicionar. Debe ser una de las claves de self.widgetsDict. Si es None, actualiza la posición de todos los widgets.
        """
        layout = self.layouts[self.current_state]
        for widget, (x,y) in layout.items():
             self.place_widget(widget, x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_positions()

    def modo_init(self):
        self.place_widget("cruz", 0.5, 0.4)
        self.place_widget("label_orden", 0.5, 0.5)

    def modo_cue(self):
        self.place_widget("cruz", 0.1, 0.3)
        self.place_widget("label_orden", 0.1, 0.1)
    
    def modo_rest(self):
        self.place_widget("cruz", 0.5, 0.5)
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    _ventana = StimuliWindow()
    _ventana.show()
    app.exec_()