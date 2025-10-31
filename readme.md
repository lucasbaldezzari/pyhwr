# Handwriting Project (Python)

<img align="right" src="neuroialogo.png" alt="Neuro-IA Lab" width="210">

Proyecto para estudiar la factibilidad de decodificación del trazo continuo de letras del alfabeto español a partir del electroencefalograma.

Este repositorio contiene los script en Python para generar, gestionar y almacenar eventos. Enviar mensajes hacia la tablet donde se presentan los estímulos, recibir mensajes de la tablet, entre otras tareas.

La aplicación de la tablet puede encontrarse en [Handwriting Project - Android app](https://github.com/lucasbaldezzari/handwritingrecording)

#### Versión 0.0.3

- Corrección de bugs menores.
- Se generan clases para poder manejar los datos registrados por el g.HIAMP que se almacenan en archivos _hdf5_ y los datos de los archivos _xdf_ de Lab Streaming Layer. 

#### Versión 0.0.1

- Comunicación bidireccional entre PC y Tablet.
- Envío de eventos por LSL.
- Generación de interfaz gráfica para usarlo con sensores ópticos de trigbox de gtec.

## Cominucación USB

En este proyeco, para poder conectar la PC o Laptop a la tablet es necesario contar con *Android Debug Bridge (adb)*.

Para instalar *adb* se debe ingresar a la página oficial de Android Developers y descargar la versión adecuada desde [acá](https://developer.android.com/tools/releases/platform-tools). Una vez descargado, descomprimir y agregar la carpeta a las Variables de Entorno de Windows, de esta manera, se podrá ejecutar *adb* desde consola.

NOTA: Podes encontrar la versión utilizada en este proyecto dentro de la carpeta [adb]() de este repositorio.