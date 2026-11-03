@AGENTS.md

# Notas para Claude Code

- Cada sesión trabaja un hito o una disposición. Empezar con `/hito <Mx>` o
  `/nueva-disposicion <sección>`; terminar con `/verificar` y `/cierre`.
- Antes de tocar un capítulo, leer `docs/ROADMAP.md`, `docs/decisions.md` y `docs/chapter-<x>.md`
  si existe. Si el PDF no está en `references/`, detenerse y pedirlo.
- Cada función de `codes/` cita en su docstring la sección, la ecuación y la página de S100-24.
- Los coeficientes de tablas (G5, B4.1-1, A3.1) se transcriben con su página; nunca se completan
  de memoria.
- El oráculo de un capítulo lo escribe el subagente `revisor-normativo` o una sesión aparte,
  sin leer `src/cfs_design`.
- Comandos de verificación en Windows (PowerShell) y Linux: los mismos de CONTRIBUTING.md.
