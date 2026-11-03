# Reglas de trabajo de StructureLab_CFS

## Alcance

- El repositorio calcula la resistencia de miembros de acero formado en frío según
  AISI S100-24 (North American Specification, edición 2024), solo LRFD (no añadir ASD ni LSD).
- Se implementan los dos métodos de la norma: Método de Resistencia Directa (DSM: E3.2, E4,
  F3.2, F4) y Método del Ancho Efectivo (EWM: E3.1, F3.1 y Apéndice 1). Ninguno sustituye al otro.
- Estado actual: hito M0 (esqueleto). Ningún capítulo está implementado; el motor devuelve
  `INCOMPLETE`. Los capítulos entran en el orden de la [hoja de ruta](docs/ROADMAP.md), uno por vez.
- Fuente normativa: el PDF de S100-24 en `references/` (ignorada por Git; no versionar PDF).
  El AISI Cold-Formed Steel Design Manual y CUFSM sirven para contrastar, no son norma.
- Decisiones de proyecto: [decisions.md](docs/decisions.md). Decisiones por capítulo: `docs/chapter-<x>.md`.
- Antes de trabajar, registrar rama/SHA y cambios locales. No borrar trabajo del usuario ni
  archivos no versionados desconocidos; no cambiar permisos.
- Sin commit ni push salvo autorización.

## Arquitectura

- Una fuente de verdad por concepto ([arquitectura](docs/architecture.md)): fórmulas y φ en
  `codes/aisi_s100_24/<capítulo>.py`; propiedades de pared delgada en `sections/`; cargas
  críticas elásticas en `buckling/`; selección y cálculo en `domain/<capítulo>.py`; límites de
  B4.1 en `domain/applicability.py`; obligaciones independientes en `domain/coverage.py`.
- Las propiedades de sección se calculan desde la geometría; el catálogo guarda dimensiones,
  nunca propiedades.
- Las interfaces (CLI, web) llaman a `engine`/`execution`; nunca calculan capacidades.
- No fusionar ecuaciones por parecido algebraico; exigir equivalencia de norma, dominio,
  unidades y estado límite.
- No añadir clases, servicios, registros o dependencias sin necesidad demostrada. Las
  dependencias numéricas (p. ej. pyCUFSM) van como extra opcional, nunca en el núcleo.
- Eliminar el código sustituido en la misma tarea; sin fachadas sin consumidores.

## Exactitud normativa

- Para cambiar una regla, identificar sección, ecuación, página, condiciones y unidades;
  distinguir Specification, User Note y Commentary.
- Transcribir del PDF; nunca escribir ecuaciones ni coeficientes de memoria (S100-24 cambió,
  entre otras, la forma de la Ec. E4-1 respecto a ediciones anteriores).
- No suponer valores (Fu, longitudes, Cb, Lm, caso de web crippling) por ausencia de datos:
  bloquear con error estructurado (`INCOMPLETE`).
- Fuera de los límites de la Tabla B4.1-1 del método pedido: `INCOMPLETE` con la variable y el
  límite. B4.2 no se automatiza.
- Una decisión que S100-24 no resuelve inequívocamente se consulta al usuario (problema,
  referencia, alternativas, consecuencias, recomendación) y se registra en el documento que
  corresponda.
- `PASS` solo para el alcance declarado, con todas las obligaciones cumplidas.
- `float` en el cálculo; redondeo solo para presentación.

## Verificación

- Seguir [CONTRIBUTING.md](CONTRIBUTING.md). Cambios de cálculo requieren casos en el oráculo
  independiente (`tests/oracles/<capítulo>.py`, en Decimal, sin importar el paquete).
- El oráculo no lo escribe la misma sesión que escribe la implementación.
- No modificar valores de referencia para hacer pasar un cambio.
- Cerrar cada tarea con: cambios, pruebas reales (comando y resultado), diferencias numéricas,
  riesgos y pendientes.
