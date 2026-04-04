# Pruebas piloto

## Pruebas de rondas por separado

### 1. Testeo de marcadores

Se busca testear:

- [ ] Que todos los eventos importantes generados en la tablet y la PC se almacenen correctamente para cada tipo de task (emg, eog, basal, entrenamiento/ejectuado/imaginado).

Files creados:

1. sub-test_eventos_ses-test_eventos_task-ejecutada_run-01_eeg: Contiene 240 trials. Sin trazos. Se eveluó que todos los marcadores y eventos sean registrados correctamente. Commit de handwritting app (f9aba4f33b02c4b8e44af876fb0faacd11fc9a2d)
2. sub-contrazos_ses-02_task-ejecutada_run-01_eeg y sub-contrazos_ses-02_task-ejecutada_run-02_eeg. Rondas de 40 trials cada una. Se realizaron trazos. Commit de handwritting app (7126d40e7652d4a649170119d1a9db3492c78bdc).

### 2. Testeo de trazos y marcadores

- [ ] Volver a evaluar el punto _Testeo de marcadores_ y además corroborar que todos los trazos generados en la tablet para cada letra (cada trial) se vean correctamente (se debe leer la información de cada trazo y plotearlo para evaluar visualmente).

### 3. Testeo reonda de EMG

Sólo registrar EMG.

- [ ] Corroborar que se registran eventos para la ronda de EMG.
- [ ] Corroborar que se registran correctamente las señales de EMG para cada canal.

### 4. Testeo de ronda EOG

Sólo registrar EOG.

- [ ] Corroborar que se registran eventos para la ronda de EOG.
- [ ] Corroborar que se registran correctamente las señales de EOG para cada canal.

## 5. Testeo de ronda EEG, EMG y EOG

Registrar todas las señales para algunas rondas de entrenamiento (10 trials, una letra diferente en cada trial).

- [ ] Corroborar que se registran eventos para la ronda de EEG.
- [ ] Corroborar que se registran y almacenan correctamente cada una de las señales.

## Pruebas experimento completo

Se prueba el experimento completo en personas voluntarias. Es decir, se lleva a cabo todo lo que se dice en el protocolo experimental, esto es:

- Completar el formulario online previo a la sesión.
- Colocación de electrodos de EEG, EMG y EOG.
- Registro de ronda EMG.
- Registro de ronda EOG.
- Registro basal.
- Registro de _cuatro_ rondas ejecutadas.
- Registro de _cuatro_ rondas imaginadas (con sus registros basales entre cada ronda).


