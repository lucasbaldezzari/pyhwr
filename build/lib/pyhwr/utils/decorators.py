import time
from functools import wraps

class TimerLogger:
    def __init__(self):
        self.timestamps = []

def intervalCounter(logger):
    """
    Función decoradora para medir el tiempo entre llamadas a la función decorada.
    Guarda los tiempos en milisegundos en logger.timestamps.

    Params:
        logger (TimerLogger): Instancia de TimerLogger donde se guardarán los tiempos.
    Returns:
        Decorador que envuelve la función original.
    Uso:
        @intervalCounter(logger)
        def my_function():
            # Código de la función
            pass
    """
    def decorator(func):
        last_time = [None] #debe ser una lista mutable para mantener el estado entre llamadas
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.perf_counter() # Usamos perf_counter para mayor precisión
            if last_time[0] is not None: # Verificamos si es la primera llamada
                logger.timestamps.append((now - last_time[0]) * 1000)
            last_time[0] = now
            return func(*args, **kwargs) # Llamamos a la función original
        return wrapper # Decorador que envuelve la función original
    return decorator # Decorador que envuelve la función original