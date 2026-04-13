# SquareWidget

## Descripción general

`SquareWidget` es un componente visual liviano basado en `QWidget` que implementa un rectángulo o cuadrado flotante, sin marco, con fondo coloreado y contenido textual centrado. El widget está pensado para funcionar como overlay de apoyo dentro de la interfaz experimental, especialmente para mostrar estados de sesión, marcadores visuales y mensajes breves de alto contraste. fileciteturn31file0

Dentro de la arquitectura del proyecto, `SquareWidget` se utiliza como bloque de UI reutilizable en gestores como `SessionManager` y `PreExperimentManager`, donde aparece como panel informativo y como indicador visual de fases o calibración. fileciteturn30file4 fileciteturn30file5

## Responsabilidad del módulo

La clase encapsula cuatro responsabilidades principales:

1. renderizar una superficie rectangular con color de fondo configurable;
2. mostrar texto enriquecido en HTML centrado verticalmente dentro del widget;
3. permitir modificación dinámica de texto, color, tamaño y geometría durante la ejecución;
4. ofrecer una interacción manual simple mediante arrastre con mouse y administración global de instancias activas. fileciteturn31file0

No implementa lógica experimental, sincronización temporal ni comunicación con otros componentes. Su función es puramente visual y de soporte para otras clases de nivel superior. fileciteturn31file0

## Dependencias principales

El widget depende de PyQt5 y utiliza las siguientes piezas:

- `QWidget` como clase base;
- `QPainter`, `QFont` y `QPen` para el renderizado;
- `QColor` para el manejo de color;
- `QTextDocument` para dibujar texto HTML;
- `QPoint` para gestionar el desplazamiento durante el arrastre. fileciteturn31file0

## Clase principal

### `SquareWidget`

```python
class SquareWidget(QWidget)
```

Clase que representa un widget rectangular o cuadrado de apariencia flotante.

### Constructor

```python
SquareWidget(
    x=100,
    y=100,
    width=100,
    height=None,
    color="red",
    parent=None,
    font_size=14,
    text="",
    text_color="white",
    show_on_init=True,
    auto_font_resize=False,
)
```

#### Parámetros

- `x`, `y`: posición inicial del widget en pantalla.
- `width`: ancho inicial del widget.
- `height`: alto inicial. Si es `None`, se utiliza el mismo valor que `width`, generando un cuadrado.
- `color`: color de fondo del widget.
- `parent`: widget padre opcional.
- `font_size`: tamaño base de fuente.
- `text`: contenido textual inicial.
- `text_color`: color del texto.
- `show_on_init`: controla si el widget se muestra inmediatamente al construirse.
- `auto_font_resize`: habilita el cálculo automático del tamaño de fuente según la geometría del widget. fileciteturn31file0

### Estado interno relevante

La implementación mantiene los siguientes atributos principales:

- `self.width` y `self.height`: dimensiones internas usadas para dibujo y resize;
- `self.square_color`: color de fondo (`QColor`);
- `self.text`: texto renderizado;
- `self.text_color`: color del texto (`QColor`);
- `self.font_size`: tamaño base de fuente;
- `self.auto_font_resize`: bandera de autoajuste tipográfico;
- `self.active`: estado lógico de visibilidad/renderizado;
- `self.dragging`: bandera de arrastre;
- `self.offset`: desplazamiento relativo del mouse;
- `SquareWidget.instances`: registro de instancias vivas de la clase. fileciteturn31file0

## Comportamiento visual

El constructor fija la geometría inicial con `setGeometry(...)`, establece flags de ventana `Qt.FramelessWindowHint | Qt.SubWindow` y activa `Qt.WA_TranslucentBackground`, por lo que el widget se comporta como una ventana liviana, sin decoración, útil para overlays o paneles auxiliares. fileciteturn31file0

El método `paintEvent(...)` dibuja un rectángulo sólido con borde negro y luego renderiza el contenido textual mediante `QTextDocument`, lo que permite utilizar HTML simple para aplicar tamaño, color, negrita, cursiva o alineación. El texto se posiciona con centrado vertical respecto de la altura del widget. fileciteturn31file0

## Métodos públicos

### `change_text(text)`

Actualiza el contenido textual y fuerza repintado con `update()`. fileciteturn31file0

### `change_text_color(color)`

Actualiza el color del texto y solicita repintado. fileciteturn31file0

### `change_font_size(size)`

Modifica el tamaño de fuente base. fileciteturn31file0

### `set_font_size(size)`

Alias semántico de `change_font_size(...)`. fileciteturn31file0

### `get_font_size()`

Devuelve el tamaño de fuente actual. fileciteturn31file0

### `enable_auto_font_resize(enable=True)`

Activa o desactiva el cálculo automático del tamaño de fuente en función del lado menor del widget. fileciteturn31file0

### `change_color(color)`

Cambia el color de fondo. fileciteturn31file0

### `resize_rectangle(new_width, new_height)`

Redimensiona el widget, actualiza las dimensiones internas y fija el nuevo tamaño con `setFixedSize(...)`. fileciteturn31file0

### `activate()`

Marca el widget como activo, lo muestra y solicita repintado. fileciteturn31file0

### `deactivate()`

Marca el widget como inactivo y lo oculta. fileciteturn31file0

### `move_to(x, y)`

Reposiciona el widget usando coordenadas absolutas. fileciteturn31file0

### `close_all()`

Método de clase que cierra todas las instancias registradas en `SquareWidget.instances` y limpia el registro global. fileciteturn31file0

## Eventos relevantes

### `paintEvent(event)`

Implementa el dibujo del fondo y del texto. El evento no se invoca manualmente; Qt lo dispara cuando corresponde redibujar el widget. fileciteturn31file0

### `mousePressEvent(event)`

Inicia el arrastre si se presiona el botón izquierdo y el widget está activo. fileciteturn31file0

### `mouseMoveEvent(event)`

Desplaza el widget mientras el estado de arrastre permanece activo. fileciteturn31file0

### `mouseReleaseEvent(event)`

Finaliza el arrastre. fileciteturn31file0

### `closeEvent(event)`

Elimina la instancia del registro global antes de delegar al comportamiento estándar de Qt. fileciteturn31file0

## Integración en la arquitectura

En `SessionManager`, la clase se utiliza para construir al menos tres overlays:

- un panel de información de sesión (`information_label`),
- un marcador visual de cue (`marcador_cue`),
- un widget de calibración (`marcador_calibration`). fileciteturn30file4

En `PreExperimentManager`, además del panel de información, se agrega un widget específico para marcar el inicio de ronda (`marcador_inicio`), junto con los widgets de cue y calibración. fileciteturn30file5

Esta reutilización muestra que `SquareWidget` se concibe como un componente base de overlays configurables dentro del front-end experimental. fileciteturn30file4turn30file5

## Ejemplo de uso

```python
from PyQt5.QtWidgets import QApplication
from pyhwr.widgets import SquareWidget
import sys

app = QApplication(sys.argv)

widget = SquareWidget(
    x=200,
    y=200,
    width=300,
    height=120,
    color="#202020",
    text="<div style='font-size:24px; text-align:center;'><b>CUE</b></div>",
    text_color="white",
    show_on_init=True,
)

widget.change_color("#000000")
widget.change_text("<div style='font-size:20px; text-align:center;'>Estado activo</div>")

sys.exit(app.exec_())
```

## Observaciones de diseño

### 1. Uso de `self.width` y `self.height`

La clase define atributos llamados `width` y `height`, lo que puede generar ambigüedad conceptual con los métodos heredados `width()` y `height()` de `QWidget`. Aunque el código funciona porque accede a atributos y no a métodos, conviene tenerlo presente al extender la clase o integrarla con otras utilidades de Qt. fileciteturn31file0

### 2. Renderizado de texto HTML

El uso de `QTextDocument` permite textos ricos, pero implica que el widget no se limita a texto plano. El contenido debe considerarse como HTML renderizable, no como una simple cadena a pintar con `drawText(...)`. fileciteturn31file0

### 3. Gestión global de instancias

El atributo de clase `instances` facilita el cierre masivo mediante `close_all()`. Esta decisión es útil para overlays transitorios, aunque introduce estado global compartido entre instancias. fileciteturn31file0

### 4. Interacción manual incorporada

La clase permite arrastre con el mouse por defecto. Esto la vuelve práctica para pruebas visuales o reajustes manuales en ejecución, aunque puede no ser deseable en contextos de producción cerrada si se requiere una UI estrictamente fija. fileciteturn31file0

## Limitaciones actuales

- No existe soporte explícito para bordes configurables, esquinas redondeadas o padding avanzado.
- No se implementa layout interno; todo el contenido se dibuja manualmente.
- El cálculo automático de fuente utiliza una heurística simple basada en el lado menor del widget.
- La clase no expone señales Qt propias para notificar cambios de estado o interacción. fileciteturn31file0

## Recomendaciones de mejora

1. Renombrar `self.width` y `self.height` por nombres menos ambiguos, por ejemplo `rect_width` y `rect_height`.
2. Incorporar opciones de borde, radio de esquina y alineación horizontal explícita.
3. Agregar una política opcional para deshabilitar arrastre en entornos de ejecución bloqueados.
4. Separar la representación visual del registro global de instancias si se busca una clase más desacoplada. fileciteturn31file0

## Resumen

`SquareWidget` constituye un componente utilitario de UI para mostrar overlays rectangulares con texto HTML, color configurable y manipulación dinámica en tiempo de ejecución. Su diseño es simple, directo y funcional para paneles auxiliares dentro del pipeline experimental, especialmente en los gestores que controlan sesiones y pre-experimentos. fileciteturn31file0turn30file4turn30file5
