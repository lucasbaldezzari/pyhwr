from datetime import datetime

class InstrumentoError(Exception):
    pass

class AnioFabricacionError(InstrumentoError):
    pass

class ResolucionInvalidaError(InstrumentoError):
    pass

class EstadoInvalidoError(InstrumentoError):
    pass

class Investigador:
    def __init__(self, nombre: str, dni: str, especialidad: str):
        self.nombre = nombre
        self.dni = dni
        self.especialidad = especialidad

    def __str__(self):
        return f"Investigador: {self.nombre} (DNI: {self.dni}, Especialidad: {self.especialidad})"

class Instrumento:
    cantidad_instrumentos = 0

    def __init__(self, nombre: str, marca: str, numero_serie: str,
                 anio_fabricacion: int, investigador_asignado=None):
        if anio_fabricacion < 1990:
            raise AnioFabricacionError("El año de fabricación debe ser mayor o igual a 1990.")
        if investigador_asignado is not None and not isinstance(investigador_asignado, Investigador):
            raise EstadoInvalidoError("El investigador asignado debe ser una instancia de Investigador o None.")
        self.nombre = nombre
        self._marca = marca
        self.__numero_serie = numero_serie
        self.anio_fabricacion = anio_fabricacion
        self.investigador_asignado = investigador_asignado
        Instrumento.cantidad_instrumentos += 1

    def informacion_basica(self):
        info = f"Instrumento: {self.nombre}, Marca: {self._marca}, Año: {self.anio_fabricacion}"
        if self.investigador_asignado:
            info += f", Asignado a: {self.investigador_asignado.nombre}"
        return info

    def asignar_investigador(self, investigador: Investigador):
        if not isinstance(investigador, Investigador):
            raise EstadoInvalidoError("Debe ser una instancia de Investigador.")
        self.investigador_asignado = investigador

    def get_numero_serie(self):
        return self.__numero_serie

    def __str__(self):
        return f"{self.nombre} ({self._marca}, {self.anio_fabricacion})"

class InstrumentoAnalogico(Instrumento):
    def __init__(self, nombre: str, marca: str, numero_serie: str, anio_fabricacion: int, escala_maxima: float, sensibilidad: float, investigador_asignado=None):
        super().__init__(nombre, marca, numero_serie, anio_fabricacion, investigador_asignado)
        self.escala_maxima = escala_maxima
        self.sensibilidad = sensibilidad

    def informacion_basica(self):
        info = super().informacion_basica()
        info += f", Escala máxima: {self.escala_maxima}, Sensibilidad: {self.sensibilidad}"
        return info

    def necesita_calibracion(self):
        current_year = datetime.now().year
        return (current_year - self.anio_fabricacion > 5) and (self.sensibilidad > 0.8)

class InstrumentoDigital(Instrumento):
    def __init__(self, nombre: str, marca: str, numero_serie: str, anio_fabricacion: int, resolucion_bits: int, tiene_usb: bool, investigador_asignado=None):
        if resolucion_bits not in [8, 12, 16, 24]:
            raise ResolucionInvalidaError("La resolución en bits debe ser 8, 12, 16 o 24.")
        super().__init__(nombre, marca, numero_serie, anio_fabricacion, investigador_asignado)
        self.resolucion_bits = resolucion_bits
        self.tiene_usb = tiene_usb

    def informacion_basica(self):
        info = super().informacion_basica()
        info += f", Resolución bits: {self.resolucion_bits}, Tiene USB: {self.tiene_usb}"
        return info

    def necesita_actualizacion(self):
        current_year = datetime.now().year
        return (current_year - self.anio_fabricacion > 3) and not self.tiene_usb

# Ejemplos de funcionamiento (como en el examen)
ana = Investigador("Ana Martinez", "30123456", "Biofisica")
instr1 = InstrumentoAnalogico("Multimetro", "Hp", "A1234", 2015, escala_maxima=100, sensibilidad=0.85)
instr1.asignar_investigador(ana)
print(instr1.informacion_basica())
print(instr1.necesita_calibracion())  # Debería ser True en 2025 (2015 + 10 > 5 y 0.85 > 0.8)

# Ejemplo adicional para InstrumentoDigital
instr2 = InstrumentoDigital("Osciloscopio", "Tektronix", "B5678", 2020, resolucion_bits=12, tiene_usb=True)
print(instr2.informacion_basica())
print(instr2.necesita_actualizacion())  # Debería ser True en 2025 (2020 + 5 > 3 y no USB? Espera, tiene_usb=True, así que False)

# Ejemplos para demostrar errores
try:
    instr_error_anio = Instrumento("Error", "Marca", "S123", 1985)  # Año inválido
except AnioFabricacionError as e:
    print(f"Error capturado: {e}")

try:
    instr_error_res = InstrumentoDigital("Error", "Marca", "S123", 2000, resolucion_bits=10, tiene_usb=False)  # Bits inválidos
except ResolucionInvalidaError as e:
    print(f"Error capturado: {e}")

try:
    instr_error_estado = Instrumento("Error", "Marca", "S123", 2000, investigador_asignado=None)  # Asignado inválido
except EstadoInvalidoError as e:
    print(f"Error capturado: {e}")

try:
    instr3 = Instrumento("Valido", "Marca", "S123", 2000)
    instr3.asignar_investigador("no es objeto")  # Asignación inválida
except EstadoInvalidoError as e:
    print(f"Error capturado: {e}")

# Mostrar conteo de instrumentos
print(f"Cantidad total de instrumentos creados: {Instrumento.cantidad_instrumentos}")