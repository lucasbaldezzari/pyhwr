# API Documentation — `SquareWidget`

## Overview

`SquareWidget` is a lightweight `QWidget` subclass designed to display a colored rectangular overlay with centered HTML text. It is used in the experimental control UI as an auxiliary visual widget rather than as a layout-managed application panel.

In the current architecture, `SessionManager` uses `SquareWidget` to render external floating indicators such as the session information panel, the cue marker, and the calibration marker. Because the widget is frameless, translucent, and independently positioned, it behaves more like a movable overlay than a standard child widget in a Qt layout.

## Class signature

```python
class SquareWidget(QWidget):
```

## Main responsibilities

- Render a rectangular or square colored surface.
- Render centered HTML-formatted text inside the rectangle.
- Allow dynamic updates of color, text, text color, font size, and geometry.
- Support drag-and-drop repositioning with the mouse.
- Track all living instances through a class-level registry to allow mass closing.

## Constructor

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
    auto_font_resize=False
)
```

### Parameters

- `x`, `y` (`int`): Initial screen position of the widget.
- `width` (`int`): Initial width of the widget.
- `height` (`int | None`): Initial height. If `None`, the widget becomes square and uses `width`.
- `color` (`str | QColor-compatible`): Background color.
- `parent` (`QWidget | None`): Optional Qt parent.
- `font_size` (`int`): Base font size used when `auto_font_resize=False`.
- `text` (`str`): HTML-capable text content rendered inside the widget.
- `text_color` (`str | QColor-compatible`): Foreground text color.
- `show_on_init` (`bool`): If `True`, the widget is shown immediately after construction.
- `auto_font_resize` (`bool`): If `True`, font size is derived from widget size.

## Stored state

### Geometry and appearance

- `self.width`
- `self.height`
- `self.square_color`
- `self.text`
- `self.text_color`
- `self.font_size`
- `self.auto_font_resize`

### Interaction state

- `self.active`: Enables or disables painting and dragging behavior.
- `self.dragging`: Indicates whether the widget is currently being dragged.
- `self.offset`: Mouse offset used to compute dragging motion.

### Class-level registry

- `SquareWidget.instances`: List of all currently alive `SquareWidget` instances.

## Public API

### `paintEvent(event)`

Handles painting. It fills the rectangle, computes the effective font size, and renders HTML text through `QTextDocument`.

Important implementation details:
- If `self.active` is `False`, the method returns immediately.
- Background is drawn using `QPainter.drawRect(...)`.
- Text is vertically centered by translating the painter before calling `doc.drawContents(...)`.
- HTML rendering means content may include styled spans, line breaks, and inline formatting.

### `change_text(text)`

Updates the displayed text and triggers repaint.

### `change_text_color(color)`

Updates text color and triggers repaint.

### `change_font_size(size)`

Updates the base font size and triggers repaint.

### `set_font_size(size)`

Readable alias for `change_font_size(...)`.

### `get_font_size() -> int`

Returns the current base font size.

### `enable_auto_font_resize(enable=True)`

Turns automatic font resizing on or off.

### `change_color(color)`

Updates the background color and triggers repaint.

### `resize_rectangle(new_width, new_height)`

Changes the widget dimensions and applies the new fixed size.

Note that this method updates both internal attributes and Qt size constraints.

### `activate()`

Marks the widget as active, shows it, and repaints it.

### `deactivate()`

Marks the widget as inactive and hides it.

### `move_to(x, y)`

Moves the widget to the given screen coordinates.

### `close_all()` (class method)

Closes every tracked instance and clears the registry.

This is useful when the experiment creates multiple floating widgets and they all need to be cleaned up reliably.

## Interaction events

### `mousePressEvent(event)`

Starts dragging when the left mouse button is pressed and the widget is active.

### `mouseMoveEvent(event)`

Moves the widget while dragging is active.

### `mouseReleaseEvent(event)`

Stops dragging.

### `closeEvent(event)`

Removes the instance from `SquareWidget.instances` before delegating to the parent implementation.

## Example usage

### Minimal example

```python
widget = SquareWidget(
    x=200,
    y=200,
    width=300,
    height=150,
    color="#ebebeb",
    text="<b>Información</b><br>Run 1",
    text_color="black"
)
```

### Dynamic updates

```python
widget.change_text("<b>CUE</b>")
widget.change_color("black")
widget.change_text_color("white")
widget.set_font_size(20)
widget.resize_rectangle(250, 250)
```

### Integration with `SessionManager`

```python
self.information_label = SquareWidget(
    x=200,
    y=200,
    width=650,
    height=400,
    color="#ebebeb",
    text=text
)

self.marcador_cue = SquareWidget(
    x=200,
    y=650,
    width=250,
    height=250,
    color="black",
    text=text,
    text_color="white"
)
```

## Design observations

### 1. The widget is overlay-oriented, not layout-oriented

Because it uses:
- `Qt.FramelessWindowHint | Qt.SubWindow`
- `Qt.WA_TranslucentBackground`

and explicit geometry positioning, it is best understood as a free-floating overlay widget.

### 2. HTML text support is a strong feature

Using `QTextDocument.setHtml(...)` makes it suitable for rich status panels without introducing extra `QLabel` or layout complexity.

### 3. The class stores `width` and `height` as instance attributes

This is convenient internally, but it shadows the semantic role of inherited Qt geometry accessors such as `width()` and `height()`. Although the current implementation works, it is not ideal API design for a Qt subclass.

### 4. `deactivate()` hides the widget entirely

This means inactive widgets are not merely skipped during painting; they also disappear from view.

## Recommendations

- Rename `self.width` and `self.height` to `rect_width` and `rect_height` to avoid confusion with inherited QWidget geometry methods.
- Consider adding a border color and border thickness API for more flexible marker rendering.
- If these widgets are always children of another window, consider documenting coordinate semantics explicitly.
- If drag support is only for debugging, make it optional through a constructor flag.

## Summary

`SquareWidget` is a small but useful utility widget for experimental UI overlays. Its strengths are:
- fast instantiation,
- HTML text rendering,
- direct visual manipulation,
- simple runtime mutation.

It is well suited for temporary markers and floating information panels, especially in the current `SessionManager` workflow.
