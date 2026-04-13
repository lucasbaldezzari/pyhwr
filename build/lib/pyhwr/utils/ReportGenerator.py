import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
import logging
import json
from pyhwr.managers import LSLDataManager, GHiampDataManager
pd.options.display.float_format = '{:.2f}'.format

class RunReportGenerator:
    """
    Clase que permite generar reportes para una ronda de experimento, entre la info generada se tiene,
    número de trials, tabla con tiempos de cada trial y cues, tiempo promedio entre trials,
    tiempo promedio de cues, letras mostradas a la persona, gráficos de cada trazo registrado,
    tiempos desde el inicio del cue al primer pendown registrado, cantidad de pendown detectados
    por trial, tiempos entre el primer pendown y el último evento de trazado de letra registrado,
    y otros datos/características que puedan ser de utilidad para la validación y análisis.

    La clase genera reportes sólo si los archivos de datos de LSL y gHIAMP contienen información.
    Es decir, es posible generar reportes de ambos, o de sólo uno de ellos.

    
    TO IMPLEMENTE: Capaz los reportes se pueden generar en formato HTML o PDF, con gráficos incluidos.
    Para esto se pueden usar librerías como ReportLab (PDF) o Jinja2 (HTML). El reporte podría incluir:
    - Resumen general de la ronda (número de trials, letras mostradas, etc.)
    - Tabla con tiempos de cada trial y cues.
    - Gráficos de cada trazo registrado (coordenadas x-y, tiempos, etc.)
    - Análisis de tiempos (tiempo promedio entre trials, tiempo promedio de cues, etc
    - Análisis de eventos de trazado (tiempos desde el inicio del cue al primer pendown,
    cantidad de pendown por trial, tiempos entre el primer pendown y el último evento de trazado, etc.)
    - Gráficos de los trazos en una sóla hoja, letras por columna y cada trial en una fila. Se podría también
    graficar el trazo "promedio" con sus desvíos en la última fila.
    - VER MÁS

    - Keys esperados en LSLDataManager.streamers_keys:
    {'Laptop_Markers': ['trialID', 'letter', 'runID', 'sessionStartTime', 'trialStartTime', 'trialPrecueTime', 'trialCueTime',
    'trialFadeOffTime', 'trialRestTime', 'sessionFinalTime'],
    'Tablet_Markers': ['trialID', 'letter', 'runID', 'sessionStartTime', 'trialStartTime', 'trialPrecueTime', 'trialCueTime',
    'trialFadeOffTime', 'trialRestTime', 'penDownMarkers', 'penUpMarkers', 'coordinates', 'sessionFinalTime']}

    - Nombres por defecto esperados en LSLDataManager.streamers_names:
    ['Laptop_Markers', 'Tablet_Markers']
    No obstant, se podrían usar otros nombres, y puede haber sólo uno de los dos streamrs, o ambos (dependiendo el experimento).
    """

    def __init__(self, path, lsl_filename: str = None, gtec_filename: str = None):
        self.path = path
        self.lsl_filename = lsl_filename
        self.gtec_filename = gtec_filename
        self.lsl_manager = LSLDataManager(os.path.join(path, lsl_filename)) if lsl_filename else None
        self.ghiamp_manager = GHiampDataManager(os.path.join(path, gtec_filename), normalize_time=True) if gtec_filename else None
        self.report_data = {}

        ##imprimo info de los archivos cargados 
        if self.lsl_manager:
            logging.info(f"Archivo LSL cargado: {lsl_filename}.xdf")
            logging.info(f"Nombre de los marcadores en LSL: {self.lsl_manager.streamers_names}")
            logging.info(f"Cantidad de trials detectados en LSL: {self._get_trials_qty_lsl()}")
        else:
            logging.info("No se proporcionó un archivo LSL válido.")

        if self.ghiamp_manager:
            logging.info(f"Archivo g.tec cargado: {self.gtec_filename}")
        else:
            logging.info("No se proporcionó un archivo g.tec válido.")

    def sanity_check(self):
        """
        Función para revisar que los archivos contengan algo de información y caso que no, se generen errores o advertencias.
        De esta manera se evita generar reportes vacíos o sin sentido, y se asegura que el análisis se base en datos reales.
        """
        pass

    def _get_trials_qty_lsl(self):
        ## Obtiene el número de trials registrados en el archivo LSL.
        if self.lsl_manager:
            return len(self.lsl_manager.trials_info["Tablet_Markers"])
        return 0
    
    def _get_trials_qty_gtec(self):
        ## Obtiene el número de trials registrados en el archivo g.tec.
        if self.ghiamp_manager:
            return len(self.ghiamp_manager.trials_info)
        return 0

    def _extract_letters_and_coordinates(self):
        ## Extrae letras mostradas y coordenadas de los trazos registrados en el archivo LSL.
        # Esta función se puede usar para generar gráficos de los trazos y analizar las letras mostradas.
        letters = []
        coordinates = []
        if self.lsl_manager:
            for trial in self.lsl_manager.trials_info["Tablet_Markers"].values():
                letters.append(trial["letter"])
                coordinates.append(trial["coordinates"])
        return letters, coordinates
    
    def _get_pendown_lsl(self):
        """
        Función para obtener un data frame con las columnas trialID, los tiempos registrados de pendown,
        y la cantidad de pendown por trial.
        """
        pass

    def generate_report_from_lsl(self):
        ## Genera reporte a partir de datos LSL. Archivos en formato xdf con información de marcadores,
        # tiempos y coordenadas de los trazos, entre otros.
        pass

    def generate_report_from_gtec(self):
        ## Genera reporte a partir de datos g.tec. Archivos hdf5 con información de marcadores y tiempos.
        pass

    def generate_general_report(self):
        ## Genera reporte para a partir de datos LSL y g.tec
        pass

    def save_report(self, output_path):
        # Aquí se implementaría la lógica para guardar el reporte generado en un formato adecuado (por ejemplo, PDF o HTML).
        pass

if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Ejemplo de uso
    path = "test\\data\\pruebas_piloto\\testeo_marcadores\\"
    lsl_filename = "sub-test_eventos_ses-test_eventos_task-ejecutada_run-01_eeg.xdf"
    # gtec_filename = "subject_0_s3_r1.hdf5"

    report_generator = RunReportGenerator(path, lsl_filename, None)
    print(report_generator.lsl_manager.streamers_names)
    print(report_generator.lsl_manager.describe_trials())  
    print(report_generator.lsl_manager.pendown_delays)
    report_generator.lsl_manager.coordinates_info[1]["letter"] #"coordinates" o "letter"
    report_generator.lsl_manager.getTrialCoordinates(2)

    report_generator.lsl_manager.trialsTimes()

    report_generator.lsl_manager.lettersTrials("a")    
    report_generator.lsl_manager.infoTrial(40)

    fig, axes = report_generator.lsl_manager.plot_traces(2,line_color = "#12259d", show=False)
    # fig.show()
    del fig, axes
    fig, axes = report_generator.lsl_manager.plot_all_traces(figsize=(25, 10),
                                                     line_color = "#12259d", point_color="#ffffff", point_size=5,
                                                     hide_title=True, hide_axes=True, hide_ticks=True,
                                                     hide_labels=True, hide_spines=True, show=False)
    fig.show()
    del fig, axes
    
    ##PROBAR UNA RONDA DONDE NO SE DIBUJEN ALGUNAS LETRAS Y OTRAS SÍ.
    ##REVISAR POR QUÉ A VECES LA RONDA SE SINCRONIZA AL TOQUE EN LA TABLET Y OTRAS VECES DEMORA UNOS SEGUNDOS (CUANDO SE LLEGA A START)
    ##AGREGAR MÉTODO QUE INVOQUE TODOS LOS MÉTODOS DE ANÁLISIS Y GRÁFICOS Y RETORNE UN DICCIONARIO PARA USARLO LUEGO
    ##EN EL REPORTE HTML