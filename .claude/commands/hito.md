---
description: Planifica un hito de docs/ROADMAP.md y espera aprobación antes de implementar
argument-hint: <M0..M8>
---
Hito $ARGUMENTS.

1. Registra rama, SHA y cambios locales (`git status`, `git rev-parse HEAD`).
2. Lee AGENTS.md, docs/ROADMAP.md, docs/decisions.md, docs/architecture.md y los
   docs/chapter-*.md que toque el hito.
3. Lee en references/ las secciones de AISI S100-24 que cubre el hito. Si el PDF no está, detente.
4. Propón: archivos a crear o cambiar, ecuaciones por archivo (sección, ecuación, página),
   casos del oráculo, y las decisiones que S100-24 no resuelve (problema, referencia,
   alternativas, consecuencias, recomendación).
5. No escribas código hasta que el usuario apruebe el plan.
