# Proyecto: gestión de citas veterinarias (Programación II)
# Diego Ardila Quintero - 01240372038

from dataclasses import dataclass, field
from datetime import date, time, datetime
from typing import Optional

import gradio as gr
import pandas as pd

# ======================================================================
# MODELOS DEL DOMINIO
# ======================================================================

# Estados posibles de una cita
PROGRAMADA = "Programada"
CANCELADA = "Cancelada"
ATENDIDA = "Atendida"


def formato_pesos(valor: float) -> str:
    """Convierte un valor a pesos colombianos: 60000 -> '$ 60.000'."""
    return "$ " + f"{valor:,.0f}".replace(",", ".")


@dataclass
class Servicio:
    codigo: str
    nombre: str
    tarifa: float

    def __str__(self) -> str:
        return f"{self.codigo} – {self.nombre} ({formato_pesos(self.tarifa)})"


@dataclass
class Veterinario:
    cedula: str
    nombre: str
    tarjeta_profesional: str


@dataclass
class Mascota:
    nombre: str
    especie: str
    raza: str
    anio_nacimiento: int
    peso: float  # en kg

    def descripcion(self) -> str:
        return (f"{self.nombre} ({self.especie}, {self.raza}, "
                f"{self.anio_nacimiento}, {self.peso:g} kg)")


@dataclass
class Propietario:
    cedula: str
    nombre: str
    telefono: str
    municipio: str
    # clave: nombre de la mascota en minúsculas -> Mascota
    mascotas: dict[str, Mascota] = field(default_factory=dict)

    @staticmethod
    def clave_mascota(nombre: str) -> str:
        return nombre.strip().lower()


@dataclass
class Factura:
    numero: str
    fecha: date
    propietario: Propietario
    mascota: Mascota
    detalle: list[Servicio]

    @property
    def total(self) -> float:
        return sum(s.tarifa for s in self.detalle)

    def texto(self) -> str:
        """Representación de la factura en Markdown."""
        filas = "\n".join(
            f"| {s.codigo} – {s.nombre} | {formato_pesos(s.tarifa)} |"
            for s in self.detalle
        )
        return (
            f"### Factura {self.numero}\n"
            f"- **Fecha:** {self.fecha.isoformat()}\n"
            f"- **Propietario:** {self.propietario.nombre} "
            f"(C.C. {self.propietario.cedula}, tel. {self.propietario.telefono})\n"
            f"- **Mascota:** {self.mascota.descripcion()}\n\n"
            f"| Servicio | Tarifa |\n|---|---|\n{filas}\n\n"
            f"**Total: {formato_pesos(self.total)}**"
        )


@dataclass
class Cita:
    codigo: str
    fecha: date
    hora: time
    propietario: Propietario
    mascota: Mascota
    veterinario: Veterinario
    servicio: Servicio
    estado: str = PROGRAMADA
    servicios_adicionales: list[Servicio] = field(default_factory=list)
    factura: Optional[Factura] = None

    def todos_los_servicios(self) -> list[Servicio]:
        return [self.servicio] + self.servicios_adicionales


@dataclass
class Clinica:
    nit: str
    nombre: str
    codigo_dane: str
    municipio: str
    departamento: str
    direccion: str
    barrio: str
    veterinarios: dict[str, Veterinario] = field(default_factory=dict)  # por cédula
    servicios: dict[str, Servicio] = field(default_factory=dict)        # por código
    propietarios: dict[str, Propietario] = field(default_factory=dict)  # por cédula
    citas: list[Cita] = field(default_factory=list)

# ======================================================================
# LÓGICA DE NEGOCIO
# ======================================================================

class GestorCitas:
    def __init__(self) -> None:
        self.clinicas: dict[str, Clinica] = {}   # por NIT
        self._contador_citas = 0
        self._contador_facturas = 0

    # 1. Clínica -------------------------------------------------------
    def registrar_clinica(self, nit, nombre, codigo_dane, municipio,
                          departamento, direccion, barrio) -> Clinica:
        clinica = Clinica(str(nit).strip(), nombre, str(codigo_dane), municipio,
                          departamento, direccion, barrio)
        self.clinicas[clinica.nit] = clinica
        return clinica

    # 2. Veterinarios y servicios --------------------------------------
    def registrar_veterinario(self, nit, cedula, nombre, tarjeta_profesional) -> Veterinario:
        veterinario = Veterinario(str(cedula).strip(), nombre, tarjeta_profesional)
        self.clinicas[nit].veterinarios[veterinario.cedula] = veterinario
        return veterinario

    def registrar_servicio(self, nit, codigo, nombre, tarifa) -> Servicio:
        servicio = Servicio(str(codigo).strip().upper(), nombre, float(tarifa))
        self.clinicas[nit].servicios[servicio.codigo] = servicio
        return servicio

    # 3. Propietarios y mascotas ---------------------------------------
    def registrar_propietario(self, nit, cedula, nombre, telefono, municipio) -> Propietario:
        propietario = Propietario(str(cedula).strip(), nombre, str(telefono), municipio)
        self.clinicas[nit].propietarios[propietario.cedula] = propietario
        return propietario

    def registrar_mascota(self, nit, cedula_propietario, nombre, especie, raza,
                          anio_nacimiento, peso) -> Mascota:
        propietario = self.clinicas[nit].propietarios[cedula_propietario]
        mascota = Mascota(nombre, especie, raza, int(anio_nacimiento), float(peso))
        propietario.mascotas[Propietario.clave_mascota(nombre)] = mascota
        return mascota

    # 4. Programar cita ------------------------------------------------
    def programar_cita(self, nit, cedula_propietario, nombre_mascota,
                       cedula_veterinario, codigo_servicio,
                       fecha: date, hora: time) -> Cita:
        clinica = self.clinicas[nit]
        propietario = clinica.propietarios[cedula_propietario]
        mascota = propietario.mascotas[Propietario.clave_mascota(nombre_mascota)]
        self._contador_citas += 1
        cita = Cita(f"CIT-{self._contador_citas:03d}", fecha, hora, propietario,
                    mascota, clinica.veterinarios[cedula_veterinario],
                    clinica.servicios[codigo_servicio.upper()])
        clinica.citas.append(cita)
        return cita

    # 5. Cancelar cita -------------------------------------------------
    def cancelar_cita(self, nit, codigo_cita, fecha_actual: date) -> Cita:
        cita = self._cita(nit, codigo_cita)
        cita.estado = CANCELADA
        return cita

    # 6. Atender cita --------------------------------------------------
    def agregar_servicio_cita(self, nit, codigo_cita, codigo_servicio) -> Cita:
        cita = self._cita(nit, codigo_cita)
        cita.servicios_adicionales.append(self.clinicas[nit].servicios[codigo_servicio.upper()])
        return cita

    def atender_cita(self, nit, codigo_cita) -> Factura:
        cita = self._cita(nit, codigo_cita)
        self._contador_facturas += 1
        factura = Factura(f"FAC-{self._contador_facturas:03d}", cita.fecha,
                          cita.propietario, cita.mascota,
                          list(cita.todos_los_servicios()))
        cita.factura = factura
        cita.estado = ATENDIDA
        return factura

    # 7 y 8. Consultas -------------------------------------------------
    def citas_por_fecha(self, nit, fecha: date) -> list[Cita]:
        return sorted((c for c in self.clinicas[nit].citas if c.fecha == fecha),
                      key=lambda c: c.hora)

    def historial_mascota(self, nit, cedula_propietario, nombre_mascota) -> list[Cita]:
        propietario = self.clinicas[nit].propietarios[cedula_propietario]
        mascota = propietario.mascotas[Propietario.clave_mascota(nombre_mascota)]
        return sorted((c for c in self.clinicas[nit].citas if c.mascota is mascota),
                      key=lambda c: (c.fecha, c.hora))

    # Auxiliar ---------------------------------------------------------
    def _cita(self, nit, codigo) -> Cita:
        return next(c for c in self.clinicas[nit].citas if c.codigo == codigo)

# ======================================================================
# DATOS DE EJEMPLO
# ======================================================================

NIT_HUELLITAS = "901456789-1"
NIT_PATITAS = "900987654-3"


def cargar_clinicas_ejemplo(gestor: GestorCitas) -> list[str]:
    """Carga las dos clínicas del enunciado (con veterinarios y servicios).

    Devuelve los nombres de las clínicas que se cargaron (omite las que
    ya existían).
    """
    cargadas = []

    if NIT_HUELLITAS not in gestor.clinicas:
        g = gestor
        g.registrar_clinica(NIT_HUELLITAS, "Clínica Veterinaria Huellitas", "68679",
                            "San Gil", "Santander", "Calle 12 # 9-40", "Centro")
        g.registrar_veterinario(NIT_HUELLITAS, "63512478", "Juliana Ortiz Ramírez", "TP-18452")
        g.registrar_veterinario(NIT_HUELLITAS, "91254863", "Mauricio Pinzón Gómez", "TP-20117")
        for cod, nom, tar in [("CG", "Consulta general", 60000),
                              ("VAC", "Vacunación", 45000),
                              ("DES", "Desparasitación", 30000),
                              ("PEL", "Baño y peluquería", 50000)]:
            g.registrar_servicio(NIT_HUELLITAS, cod, nom, tar)
        cargadas.append("Clínica Veterinaria Huellitas")

    if NIT_PATITAS not in gestor.clinicas:
        g = gestor
        g.registrar_clinica(NIT_PATITAS, "Clínica Veterinaria Patitas Felices", "68276",
                            "Floridablanca", "Santander", "Carrera 27 # 30-15", "Cañaveral")
        g.registrar_veterinario(NIT_PATITAS, "13745821", "Sergio Arenas Villamizar", "TP-15893")
        g.registrar_veterinario(NIT_PATITAS, "37896542", "Diana Carolina Rey Moreno", "TP-22406")
        g.registrar_veterinario(NIT_PATITAS, "1098654321", "Felipe Castellanos Díaz", "TP-31578")
        for cod, nom, tar in [("CG", "Consulta general", 65000),
                              ("VAC", "Vacunación", 48000),
                              ("DES", "Desparasitación", 32000),
                              ("ECO", "Ecografía", 120000)]:
            g.registrar_servicio(NIT_PATITAS, cod, nom, tar)
        cargadas.append("Clínica Veterinaria Patitas Felices")

    return cargadas


def cargar_propietarios_ejemplo(gestor: GestorCitas) -> list[str]:
    """Carga los propietarios y mascotas de los casos de prueba.

    Carga primero las clínicas si todavía no existen. Omite los que ya existen.
    """
    cargar_clinicas_ejemplo(gestor)
    casos = [
        (NIT_HUELLITAS, "1098765432", "Laura Méndez Plata", "3157894561", "Bucaramanga",
         ("Rocky", "Perro", "Criolla", 2023, 18)),
        (NIT_HUELLITAS, "1005678912", "Camila Duarte Serrano", "3204567812", "San Gil",
         ("Copito", "Conejo", "Cabeza de león", 2025, 1.5)),
        (NIT_PATITAS, "1102345678", "Andrés Rueda Ardila", "3016789023", "Piedecuesta",
         ("Luna", "Gato", "Siamés", 2022, 4)),
    ]
    cargados = []
    for nit, ced, nombre, tel, mun, (m_nom, m_esp, m_raza, m_anio, m_peso) in casos:
        clinica = gestor.clinicas[nit]
        if ced not in clinica.propietarios:
            gestor.registrar_propietario(nit, ced, nombre, tel, mun)
            gestor.registrar_mascota(nit, ced, m_nom, m_esp, m_raza, m_anio, m_peso)
            cargados.append(nombre)
    return cargados

# ======================================================================
# INTERFAZ GRADIO
# ======================================================================

gestor = GestorCitas()

COLS_CLINICAS = ["NIT", "Nombre", "DANE", "Municipio", "Departamento", "Dirección", "Barrio"]
COLS_VETS = ["Cédula", "Nombre", "Tarjeta profesional"]
COLS_SERVS = ["Código", "Servicio", "Tarifa"]
COLS_PROPS = ["Cédula", "Propietario", "Teléfono", "Municipio", "Mascotas"]
COLS_CITAS = ["Código", "Fecha", "Hora", "Mascota", "Propietario", "Veterinario",
              "Servicios", "Estado", "Factura"]


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def _ejecutar(accion, *args):
    """Ejecuta una operación del gestor sin que la app se detenga.

    Devuelve (True, resultado) o (False, mensaje_de_error).
    """
    try:
        return True, accion(*args)
    except Exception as e:  # en esta versión no hay validaciones propias
        return False, f"Ocurrió un error: {e!r}"


def _fecha(texto: str) -> date:
    try:
        return datetime.strptime((texto or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Fecha inválida. Use el formato AAAA-MM-DD, "
                         "por ejemplo 2026-11-10.")


def _hora(texto: str):
    try:
        return datetime.strptime((texto or "").strip(), "%H:%M").time()
    except ValueError:
        raise ValueError("Hora inválida. Use el formato HH:MM en 24 horas, "
                         "por ejemplo 09:00 o 15:30.")


def _msg(ok: bool, resultado, exito: str) -> str:
    return f"✅ {exito}" if ok else f"❌ {resultado}"


def _df(filas: list[list], columnas: list[str]) -> pd.DataFrame:
    return pd.DataFrame(filas, columns=columnas)


def _clinica(nit):
    return gestor.clinicas.get(nit) if nit else None


def _filas_citas(citas) -> list[list]:
    return [[c.codigo, c.fecha.isoformat(), f"{c.hora:%H:%M}", c.mascota.nombre,
             c.propietario.nombre, c.veterinario.nombre,
             ", ".join(s.codigo for s in c.todos_los_servicios()), c.estado,
             c.factura.numero if c.factura else "—"] for c in citas]


# ----------------------------------------------------------------------
# Refresco de listas desplegables y tablas
# ----------------------------------------------------------------------
def opciones_clinicas():
    return [(f"{c.nombre} (NIT {c.nit})", c.nit) for c in gestor.clinicas.values()]


def tabla_clinicas():
    return _df([[c.nit, c.nombre, c.codigo_dane, c.municipio, c.departamento,
                 c.direccion, c.barrio] for c in gestor.clinicas.values()],
               COLS_CLINICAS)


def refrescar_clinicas(nit_actual):
    nit = nit_actual if nit_actual in gestor.clinicas else (
        next(iter(gestor.clinicas), None))
    return gr.Dropdown(choices=opciones_clinicas(), value=nit), tabla_clinicas()


def refrescar_todo(nit):
    """Actualiza todas las listas y tablas según la clínica activa."""
    c = _clinica(nit)
    propietarios = [(f"{p.nombre} ({p.cedula})", p.cedula)
                    for p in c.propietarios.values()] if c else []
    veterinarios = [(f"{v.nombre} ({v.cedula})", v.cedula)
                    for v in c.veterinarios.values()] if c else []
    servicios = [(str(s), s.codigo) for s in c.servicios.values()] if c else []
    citas = [(f"{x.codigo} | {x.fecha.isoformat()} {x.hora:%H:%M} | "
              f"{x.mascota.nombre} | {x.estado}", x.codigo)
             for x in c.citas] if c else []

    filas_vets = [[v.cedula, v.nombre, v.tarjeta_profesional]
                  for v in c.veterinarios.values()] if c else []
    filas_servs = [[s.codigo, s.nombre, formato_pesos(s.tarifa)]
                   for s in c.servicios.values()] if c else []
    filas_props = [[p.cedula, p.nombre, p.telefono, p.municipio,
                    "; ".join(m.descripcion() for m in p.mascotas.values()) or "—"]
                   for p in c.propietarios.values()] if c else []

    return (
        gr.Dropdown(choices=propietarios, value=None),   # dd_prop_mascota
        gr.Dropdown(choices=propietarios, value=None),   # dd_prop_cita
        gr.Dropdown(choices=propietarios, value=None),   # dd_prop_hist
        gr.Dropdown(choices=[], value=None),             # dd_masc_cita
        gr.Dropdown(choices=[], value=None),             # dd_masc_hist
        gr.Dropdown(choices=veterinarios, value=None),   # dd_vet_cita
        gr.Dropdown(choices=servicios, value=None),      # dd_serv_cita
        gr.Dropdown(choices=citas, value=None),          # dd_cita_cancelar
        gr.Dropdown(choices=citas, value=None),          # dd_cita_atender
        gr.Dropdown(choices=servicios, value=None),      # dd_serv_extra
        _df(filas_vets, COLS_VETS),                      # tbl_vets
        _df(filas_servs, COLS_SERVS),                    # tbl_servs
        _df(filas_props, COLS_PROPS),                    # tbl_props
    )

def cargar_mascotas(nit, cedula):
    c = _clinica(nit)
    if not c or cedula not in c.propietarios:
        return gr.Dropdown(choices=[], value=None)
    mascotas = c.propietarios[cedula].mascotas
    return gr.Dropdown(choices=[(m.nombre, k) for k, m in mascotas.items()],
                       value=None)


# ----------------------------------------------------------------------
# Manejadores de cada funcionalidad
# ----------------------------------------------------------------------
def ui_cargar_clinicas():
    ok, r = _ejecutar(cargar_clinicas_ejemplo, gestor)
    if not ok:
        return f"❌ {r}"
    if not r:
        return "ℹ️ Las clínicas de ejemplo ya estaban cargadas."
    return "✅ Datos de ejemplo cargados: " + ", ".join(r) + "."


def ui_cargar_todo():
    ok, r = _ejecutar(cargar_propietarios_ejemplo, gestor)
    if not ok:
        return f"❌ {r}"
    if not r:
        return "ℹ️ Los propietarios y mascotas de ejemplo ya estaban cargados."
    return "✅ Clínicas, propietarios y mascotas de ejemplo cargados."


def ui_registrar_clinica(nit, nombre, dane, municipio, depto, direccion, barrio):
    ok, r = _ejecutar(gestor.registrar_clinica, nit, nombre, dane, municipio,
                      depto, direccion, barrio)
    return _msg(ok, r, f"Clínica «{r.nombre}» registrada." if ok else "")


def ui_registrar_veterinario(nit, cedula, nombre, tarjeta):
    ok, r = _ejecutar(gestor.registrar_veterinario, nit, cedula, nombre, tarjeta)
    return _msg(ok, r, f"Veterinario(a) {r.nombre} registrado(a)." if ok else "")


def ui_registrar_servicio(nit, codigo, nombre, tarifa):
    ok, r = _ejecutar(gestor.registrar_servicio, nit, codigo, nombre, tarifa)
    return _msg(ok, r, f"Servicio {r.codigo} registrado." if ok else "")


def ui_registrar_propietario(nit, cedula, nombre, telefono, municipio):
    ok, r = _ejecutar(gestor.registrar_propietario, nit, cedula, nombre,
                      telefono, municipio)
    return _msg(ok, r, f"Propietario(a) {r.nombre} registrado(a)." if ok else "")


def ui_registrar_mascota(nit, cedula, nombre, especie, raza, anio, peso):
    ok, r = _ejecutar(gestor.registrar_mascota, nit, cedula, nombre, especie,
                      raza, anio, peso)
    return _msg(ok, r, f"Mascota {r.nombre} registrada." if ok else "")


def ui_programar(nit, cedula, mascota, vet, servicio, fecha, hora):
    def accion():
        return gestor.programar_cita(nit, cedula, mascota, vet, servicio,
                                     _fecha(fecha), _hora(hora))
    ok, r = _ejecutar(accion)
    if not ok:
        return f"❌ {r}"
    return (f"✅ Cita **{r.codigo}** programada para el {r.fecha.isoformat()} a las "
            f"{r.hora:%H:%M}: {r.mascota.nombre} con {r.veterinario.nombre} "
            f"({r.servicio.nombre}).")


def ui_cancelar(nit, codigo, fecha_actual):
    def accion():
        return gestor.cancelar_cita(nit, codigo, _fecha(fecha_actual))
    ok, r = _ejecutar(accion)
    return _msg(ok, r, f"La cita {r.codigo} fue cancelada y se conserva en el "
                       "historial." if ok else "")


def ui_agregar_servicio(nit, codigo, servicio):
    ok, r = _ejecutar(gestor.agregar_servicio_cita, nit, codigo, servicio)
    if not ok:
        return f"❌ {r}"
    return (f"✅ Servicio agregado a {r.codigo}. Servicios actuales: "
            + ", ".join(s.codigo for s in r.todos_los_servicios()) + ".")


def ui_atender(nit, codigo):
    ok, r = _ejecutar(gestor.atender_cita, nit, codigo)
    if not ok:
        return f"❌ {r}"
    return "✅ Cita atendida.\n\n" + r.texto()


def ui_consultar_fecha(nit, fecha):
    def accion():
        return gestor.citas_por_fecha(nit, _fecha(fecha))
    ok, r = _ejecutar(accion)
    if not ok:
        return f"❌ {r}", _df([], COLS_CITAS)
    if not r:
        return "ℹ️ No hay citas en esa fecha.", _df([], COLS_CITAS)
    return f"✅ {len(r)} cita(s) encontrada(s).", _df(_filas_citas(r), COLS_CITAS)


def ui_historial(nit, cedula, mascota):
    ok, r = _ejecutar(gestor.historial_mascota, nit, cedula, mascota)
    if not ok:
        return f"❌ {r}", _df([], COLS_CITAS)
    if not r:
        return "ℹ️ La mascota todavía no tiene citas.", _df([], COLS_CITAS)
    return f"✅ {len(r)} cita(s) en el historial.", _df(_filas_citas(r), COLS_CITAS)


# ----------------------------------------------------------------------
# Construcción de la interfaz
# ----------------------------------------------------------------------
with gr.Blocks(title="Citas veterinarias") as demo:
    gr.Markdown("# 🐾 Gestión de citas veterinarias")

    with gr.Row():
        clinica_sel = gr.Dropdown(label="Clínica activa", choices=[], value=None,
                                  scale=3)
        btn_ej1 = gr.Button("📥 Cargar clínicas de ejemplo", scale=1)
        btn_ej2 = gr.Button("📥 Cargar también propietarios y mascotas", scale=1)
    msg_ejemplo = gr.Markdown()

    # Componentes que se refrescan al cambiar de clínica o registrar datos
    with gr.Tabs():
        # ------------------------------ 1. Clínicas
        with gr.Tab("1. Clínicas"):
            with gr.Row():
                c_nit = gr.Textbox(label="NIT", placeholder="901456789-1")
                c_nombre = gr.Textbox(label="Nombre")
                c_dane = gr.Textbox(label="Código DANE")
            with gr.Row():
                c_mun = gr.Textbox(label="Municipio")
                c_dep = gr.Textbox(label="Departamento", value="Santander")
                c_dir = gr.Textbox(label="Dirección")
                c_barrio = gr.Textbox(label="Barrio")
            btn_clinica = gr.Button("Registrar clínica", variant="primary")
            msg_clinica = gr.Markdown()
            tbl_clinicas = gr.Dataframe(value=tabla_clinicas(), interactive=False,
                                        label="Clínicas registradas")

        # ------------------------------ 2. Veterinarios y servicios
        with gr.Tab("2. Veterinarios y servicios"):
            gr.Markdown("Se registran en la **clínica activa**.")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### Veterinario")
                    v_ced = gr.Textbox(label="Cédula")
                    v_nom = gr.Textbox(label="Nombre completo")
                    v_tp = gr.Textbox(label="Tarjeta profesional", placeholder="TP-18452")
                    btn_vet = gr.Button("Registrar veterinario", variant="primary")
                    msg_vet = gr.Markdown()
                with gr.Column():
                    gr.Markdown("#### Servicio del catálogo")
                    s_cod = gr.Textbox(label="Código", placeholder="CG")
                    s_nom = gr.Textbox(label="Nombre")
                    s_tar = gr.Number(label="Tarifa (COP)", precision=0)
                    btn_serv = gr.Button("Registrar servicio", variant="primary")
                    msg_serv = gr.Markdown()
            tbl_vets = gr.Dataframe(value=_df([], COLS_VETS), interactive=False,
                                    label="Veterinarios de la clínica")
            tbl_servs = gr.Dataframe(value=_df([], COLS_SERVS), interactive=False,
                                     label="Catálogo de servicios")

        # ------------------------------ 3. Propietarios y mascotas
        with gr.Tab("3. Propietarios y mascotas"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### Propietario")
                    p_ced = gr.Textbox(label="Cédula")
                    p_nom = gr.Textbox(label="Nombre completo")
                    p_tel = gr.Textbox(label="Teléfono")
                    p_mun = gr.Textbox(label="Municipio de residencia")
                    btn_prop = gr.Button("Registrar propietario", variant="primary")
                    msg_prop = gr.Markdown()
                with gr.Column():
                    gr.Markdown("#### Mascota")
                    dd_prop_mascota = gr.Dropdown(label="Propietario", choices=[])
                    m_nom = gr.Textbox(label="Nombre")
                    m_esp = gr.Textbox(label="Especie", placeholder="Perro, gato, conejo…")
                    m_raza = gr.Textbox(label="Raza")
                    m_anio = gr.Number(label="Año aproximado de nacimiento",
                                       precision=0, value=2022)
                    m_peso = gr.Number(label="Peso (kg)")
                    btn_masc = gr.Button("Registrar mascota", variant="primary")
                    msg_masc = gr.Markdown()
            tbl_props = gr.Dataframe(value=_df([], COLS_PROPS), interactive=False,
                                     label="Propietarios y mascotas")

        # ------------------------------ 4. Programar cita
        with gr.Tab("4. Programar cita"):
            with gr.Row():
                dd_prop_cita = gr.Dropdown(label="Propietario", choices=[])
                dd_masc_cita = gr.Dropdown(label="Mascota", choices=[])
            with gr.Row():
                dd_vet_cita = gr.Dropdown(label="Veterinario", choices=[])
                dd_serv_cita = gr.Dropdown(label="Servicio", choices=[])
            with gr.Row():
                t_fecha = gr.Textbox(label="Fecha (AAAA-MM-DD)", value="2026-11-10")
                t_hora = gr.Textbox(label="Hora (HH:MM)", value="09:00")
            btn_programar = gr.Button("Programar cita", variant="primary")
            msg_programar = gr.Markdown()

        # ------------------------------ 5. Cancelar cita
        with gr.Tab("5. Cancelar cita"):
            dd_cita_cancelar = gr.Dropdown(label="Cita", choices=[])
            t_fecha_cancel = gr.Textbox(
                label="Fecha en que se cancela (AAAA-MM-DD)",
                value=date.today().isoformat(),
                info="Por defecto es hoy. Cámbiela para simular otro día "
                     "(p. ej. 2026-11-11 para el caso 3 del enunciado).")
            btn_cancelar = gr.Button("Cancelar cita", variant="primary")
            msg_cancelar = gr.Markdown()

        # ------------------------------ 6. Atender cita
        with gr.Tab("6. Atender cita y facturar"):
            dd_cita_atender = gr.Dropdown(label="Cita", choices=[])
            with gr.Row():
                dd_serv_extra = gr.Dropdown(label="Servicio adicional", choices=[])
                btn_extra = gr.Button("Agregar servicio adicional")
            msg_extra = gr.Markdown()
            btn_atender = gr.Button("Atender cita y generar factura", variant="primary")
            msg_atender = gr.Markdown()

        # ------------------------------ 7. Citas por fecha
        with gr.Tab("7. Citas de una fecha"):
            q_fecha = gr.Textbox(label="Fecha (AAAA-MM-DD)", value="2026-11-10")
            btn_q_fecha = gr.Button("Consultar", variant="primary")
            msg_q_fecha = gr.Markdown()
            tbl_q_fecha = gr.Dataframe(value=_df([], COLS_CITAS), interactive=False)

        # ------------------------------ 8. Historial
        with gr.Tab("8. Historial de una mascota"):
            with gr.Row():
                dd_prop_hist = gr.Dropdown(label="Propietario", choices=[])
                dd_masc_hist = gr.Dropdown(label="Mascota", choices=[])
            btn_hist = gr.Button("Consultar historial", variant="primary")
            msg_hist = gr.Markdown()
            tbl_hist = gr.Dataframe(value=_df([], COLS_CITAS), interactive=False)

    # ---------------------------------------------------------- Eventos
    REFRESCO = [dd_prop_mascota, dd_prop_cita, dd_prop_hist, dd_masc_cita,
                dd_masc_hist, dd_vet_cita, dd_serv_cita, dd_cita_cancelar,
                dd_cita_atender, dd_serv_extra, tbl_vets, tbl_servs, tbl_props]

    def con_refresco(boton, fn, entradas, salidas):
        """Ejecuta fn y luego refresca listas y tablas de la clínica activa."""
        boton.click(fn, entradas, salidas).then(
            refrescar_todo, clinica_sel, REFRESCO)

    clinica_sel.change(refrescar_todo, clinica_sel, REFRESCO)
    dd_prop_cita.change(cargar_mascotas, [clinica_sel, dd_prop_cita], dd_masc_cita)
    dd_prop_hist.change(cargar_mascotas, [clinica_sel, dd_prop_hist], dd_masc_hist)

    # Datos de ejemplo
    for boton, fn in ((btn_ej1, ui_cargar_clinicas), (btn_ej2, ui_cargar_todo)):
        boton.click(fn, None, msg_ejemplo).then(
            refrescar_clinicas, clinica_sel, [clinica_sel, tbl_clinicas]).then(
            refrescar_todo, clinica_sel, REFRESCO)

    # 1. Clínica (también refresca la lista de clínicas)
    btn_clinica.click(
        ui_registrar_clinica,
        [c_nit, c_nombre, c_dane, c_mun, c_dep, c_dir, c_barrio], msg_clinica
    ).then(refrescar_clinicas, clinica_sel, [clinica_sel, tbl_clinicas]
    ).then(refrescar_todo, clinica_sel, REFRESCO)

    # 2 a 6
    con_refresco(btn_vet, ui_registrar_veterinario,
                 [clinica_sel, v_ced, v_nom, v_tp], msg_vet)
    con_refresco(btn_serv, ui_registrar_servicio,
                 [clinica_sel, s_cod, s_nom, s_tar], msg_serv)
    con_refresco(btn_prop, ui_registrar_propietario,
                 [clinica_sel, p_ced, p_nom, p_tel, p_mun], msg_prop)
    con_refresco(btn_masc, ui_registrar_mascota,
                 [clinica_sel, dd_prop_mascota, m_nom, m_esp, m_raza, m_anio, m_peso],
                 msg_masc)
    con_refresco(btn_programar, ui_programar,
                 [clinica_sel, dd_prop_cita, dd_masc_cita, dd_vet_cita,
                  dd_serv_cita, t_fecha, t_hora], msg_programar)
    con_refresco(btn_cancelar, ui_cancelar,
                 [clinica_sel, dd_cita_cancelar, t_fecha_cancel], msg_cancelar)
    con_refresco(btn_extra, ui_agregar_servicio,
                 [clinica_sel, dd_cita_atender, dd_serv_extra], msg_extra)
    con_refresco(btn_atender, ui_atender,
                 [clinica_sel, dd_cita_atender], msg_atender)

    # 7 y 8 (solo consultas)
    btn_q_fecha.click(ui_consultar_fecha, [clinica_sel, q_fecha],
                      [msg_q_fecha, tbl_q_fecha])
    btn_hist.click(ui_historial, [clinica_sel, dd_prop_hist, dd_masc_hist],
                   [msg_hist, tbl_hist])


demo.launch(debug=True)