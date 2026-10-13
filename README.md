# 🐾 Gestión de citas veterinarias

Aplicación en **Python + Gradio** para gestionar citas en clínicas veterinarias: registro de clínicas, veterinarios, catálogo de servicios, propietarios y mascotas; programación, cancelación y atención de citas con facturación; y consulta de agenda e historial.

Proyecto de Programación II.
**Autor:** Diego Ardila Quintero – 01240372038

---

## Funcionalidades

| # | Funcionalidad | Pestaña |
|---|---|---|
| 1 | Registrar una clínica (NIT, municipio con código DANE, dirección y barrio) | 1. Clínicas |
| 2 | Registrar veterinarios y el catálogo de servicios de una clínica | 2. Veterinarios y servicios |
| 3 | Registrar propietarios y sus mascotas (un propietario puede tener varias) | 3. Propietarios y mascotas |
| 4 | Programar una cita | 4. Programar cita |
| 5 | Cancelar una cita | 5. Cancelar cita |
| 6 | Atender una cita, agregar servicios adicionales y generar la factura | 6. Atender cita y facturar |
| 7 | Consultar las citas de una clínica en una fecha, con su estado | 7. Citas de una fecha |
| 8 | Consultar el historial de citas de una mascota | 8. Historial de una mascota |

Además, la parte superior tiene dos botones para **cargar los datos de ejemplo** y agilizar las pruebas.

---

## Requisitos

- Python 3.9 o superior
- [Gradio](https://www.gradio.org/) (4.44 o superior)
- pandas

```bash
pip install gradio pandas
```

---

## Ejecución

### En Google Colab
1. Copia todo el contenido de `citas_veterinarias.py` en una celda.
2. Si Colab no tiene Gradio, antepón una línea con `!pip install -q gradio`.
3. Ejecuta la celda: la interfaz aparece en la salida.

### En local
```bash
python citas_veterinarias.py
```
Se abre en `http://127.0.0.1:7860`.

---

## Cómo usar la aplicación

1. **Cargar datos de ejemplo** (opcional): pulsa *Cargar clínicas de ejemplo* para tener las dos clínicas del enunciado con sus veterinarios y servicios. *Cargar también propietarios y mascotas* agrega además a los propietarios de los casos de prueba.
2. **Elegir la clínica activa** en la lista de arriba. Todas las operaciones (salvo registrar una clínica) se hacen sobre ella.
3. Registrar los datos en las pestañas 1 a 3 (si no usaste los datos de ejemplo).
4. **Programar una cita** (pestaña 4): elige propietario, mascota, veterinario y servicio; escribe la fecha como `AAAA-MM-DD` (por ejemplo `2026-11-10`) y la hora como `HH:MM` en formato de 24 horas (por ejemplo `09:00`).
5. **Atender** (pestaña 6): elige la cita, agrega los servicios adicionales que haga falta y pulsa *Atender cita y generar factura*.
6. **Cancelar** (pestaña 5): elige la cita y la fecha en que se cancela. Por defecto es la fecha de hoy; cámbiala para simular otro día (por ejemplo `2026-11-11`).

Cada operación muestra un mensaje: ✅ si salió bien o ❌ con el motivo si incumple una regla. La aplicación nunca se detiene por un error.

---

## Reglas de negocio implementadas

1. Una cita está en uno de tres estados: **Programada**, **Cancelada** o **Atendida**. Al crearse queda Programada.
2. Un veterinario no puede tener dos citas en la misma fecha y hora.
3. Una mascota no puede tener dos citas en la misma fecha y hora.
   > Las reglas 2 y 3 comparan contra las citas **no canceladas** (Programadas y Atendidas), de modo que una cita cancelada libera el horario.
4. Solo se cancela una cita **Programada** y **antes de su fecha**. Las citas canceladas no se eliminan: cambian de estado y se conservan en el historial.
5. Solo se atiende una cita Programada; al atenderla pasa a Atendida y se genera la factura.
6. La factura tiene número único (`FAC-001`, `FAC-002`…), fecha, datos del propietario y de la mascota, el detalle de los servicios con su tarifa y el total (suma de tarifas). La fecha de la factura es la fecha de la cita.
7. No se permiten dos clínicas con el mismo NIT, ni dos propietarios con la misma cédula en una clínica, ni dos servicios con el mismo código en una clínica. Como validaciones adicionales, tampoco se repite la cédula de un veterinario en una clínica ni el nombre de una mascota para un mismo propietario.
8. Cuando una operación incumple una regla, se informa el motivo con un mensaje claro y la aplicación continúa.

---

## Estructura del código

Todo está en un solo archivo, organizado en secciones:

| Sección | Contenido |
|---|---|
| **Excepciones** | `ReglaNegocioError`: error con el mensaje que ve el usuario |
| **Modelos del dominio** | Dataclasses `Servicio`, `Veterinario`, `Mascota`, `Propietario`, `Factura`, `Cita`, `Clinica`; constantes de estado y `formato_pesos()` |
| **Lógica de negocio** | Clase `GestorCitas`, con un método por funcionalidad y todas las validaciones |
| **Datos de ejemplo** | `cargar_clinicas_ejemplo()` y `cargar_propietarios_ejemplo()` |
| **Interfaz Gradio** | Manejadores `ui_*`, funciones de refresco de listas y tablas, y el diseño con `gr.Blocks` |

Los códigos de cita (`CIT-001`…) y de factura (`FAC-001`…) son consecutivos y únicos para toda la aplicación. Un código solo se consume cuando la operación es aceptada.

---

## Datos de ejemplo

**Clínica Veterinaria Huellitas** – NIT `901456789-1` – San Gil (DANE 68679)
Veterinarios: Juliana Ortiz Ramírez, Mauricio Pinzón Gómez
Servicios: CG $60.000 · VAC $45.000 · DES $30.000 · PEL $50.000

**Clínica Veterinaria Patitas Felices** – NIT `900987654-3` – Floridablanca (DANE 68276)
Veterinarios: Sergio Arenas Villamizar, Diana Carolina Rey Moreno, Felipe Castellanos Díaz
Servicios: CG $65.000 · VAC $48.000 · DES $32.000 · ECO $120.000

---

## Casos de prueba

Con *Cargar también propietarios y mascotas* ya cargado:

| Caso | Qué hacer | Resultado esperado |
|---|---|---|
| **1. Cita atendida con servicio adicional** | En Huellitas, programa a **Rocky** (Laura Méndez) con Juliana, servicio CG, `2026-11-10` `09:00`. En la pestaña 6 agrega **VAC** y atiende | Cita `CIT-001` atendida; factura `FAC-001` por **$ 105.000** |
| **2. Veterinario ocupado** | Programa a **Copito** (Camila Duarte) con Juliana, DES, `2026-11-10` `09:00` | ❌ Rechazada porque la veterinaria ya tiene `CIT-001`. Con `10:00` se acepta como `CIT-002` |
| **3. Cita cancelada** | En Patitas Felices, programa a **Luna** (Andrés Rueda) con Sergio, ECO, `2026-11-12` `15:00`. Cancélala con fecha de cancelación `2026-11-11` | `CIT-003` queda Cancelada y no genera factura |
| **4. Cancelación no permitida** | Intenta cancelar `CIT-001` (ya atendida) | ❌ Rechazada: solo se cancelan citas Programadas |
| **5. Consultas** | Citas de Huellitas del `2026-11-10` y el historial de Luna | `CIT-001` Atendida y `CIT-002` Programada; en el historial de Luna, `CIT-003` Cancelada |

---

## Limitaciones

- Los datos se guardan **en memoria**: se pierden al cerrar la aplicación o reiniciar la celda de Colab.
- No hay autenticación ni control de usuarios.
- No se valida que la fecha de una cita sea futura.
