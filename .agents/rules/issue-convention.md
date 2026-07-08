---
description: Formato obligatorio para crear issues de GitHub (título con gitmoji + type, cuerpo con User Story y descripción formal, auto-etiquetado y auto-asignación). Aplica cada vez que se vaya a crear un issue en este repositorio.
---

# Formato de Issues

Al crear cualquier issue de GitHub, usa el formato definido en esta regla. El `type` y el `emoji` se toman de la **misma tabla que los commits** (`commit-convention.md`), para mantener coherencia en todo el flujo: issue → rama → commits → PR.

## Estructura del título

```
[<emoji> <type>]: <subject>
```

- El `type` y el `emoji` van juntos **entre corchetes**, en minúsculas el `type` y el gitmoji como carácter Unicode (`✨`).
- Después del corchete de cierre: dos puntos, un espacio y el `subject`.
- El `subject` describe el objetivo del issue en presente, sin punto final, en minúscula inicial.
- Mantén el título por debajo de ~72 caracteres cuando sea posible.

Ejemplos:

```
[🐛 fix]: el scraper del BCV lanza timeout al hacer scraping
[✨ feat]: agregar tasa promedio USDC P2P de Binance
[📝 docs]: actualizar guía de deployment para Vercel
[♻️ refactor]: migrar el fetch de tasas a httpx + asyncio
```

## Mapeo obligatorio type → gitmoji

Usa SIEMPRE este emoji por tipo (idéntico a `commit-convention.md`, no elijas otros):

| type       | emoji | descripción                                                              |
|------------|-------|--------------------------------------------------------------------------|
| `feat`     | ✨    | Una nueva funcionalidad                                                  |
| `fix`      | 🐛    | Corrección de un bug                                                     |
| `docs`     | 📝    | Cambios solo en documentación                                            |
| `style`    | 💄    | Cambios que no afectan el significado del código (formato, espacios)     |
| `refactor` | ♻️    | Cambio de código que no corrige bug ni añade funcionalidad               |
| `perf`     | ⚡    | Cambio de código que mejora el rendimiento                               |
| `test`     | ✅    | Añadir o corregir tests                                                  |
| `build`    | 👷    | Cambios en el sistema de build o dependencias externas                   |
| `ci`       | 💚    | Cambios en archivos y scripts de configuración de CI                     |
| `chore`    | 🔧    | Otros cambios que no modifican src ni archivos de test                   |
| `revert`   | ⏪    | Revierte un cambio anterior                                              |

## Estructura del cuerpo

El cuerpo del issue tiene **dos secciones obligatorias**: una User Story y una descripción formal de lo que ocurre. Cuando apliquen, añade también los criterios de aceptación.

```markdown
## User Story

Como <rol>, quiero <objetivo>, para <beneficio>.

## Descripción

<Descripción formal y clara de lo que ocurre o se necesita: contexto,
comportamiento actual vs. esperado (si es un bug), o el alcance de la
funcionalidad (si es un feat). Sé concreto y evita ambigüedad.>

## Criterios de aceptación

- ...
- ...
```

Ejemplo completo:

```markdown
## User Story

Como usuario, quiero que la tasa del BCV se actualice sin errores,
para consultar el tipo de cambio oficial del día de forma confiable.

## Descripción

Actualmente el endpoint de scraping del BCV lanza un timeout cuando la
página oficial tarda más de lo normal en responder, dejando la tasa sin
actualizar. Se espera que el scraper maneje el timeout con reintentos y
un fallback controlado en lugar de fallar.

## Criterios de aceptación

- El scraper reintenta ante un timeout antes de fallar.
- Si el BCV no responde, se registra el error y se conserva la última tasa válida.
- El endpoint nunca devuelve un 500 por un timeout del origen.
```

## Etiquetas automáticas según el `type`

Al crear el issue, **asigna automáticamente** la etiqueta que corresponda al `type` indicado en el título. Usa este mapeo:

| type       | label sugerida    |
|------------|-------------------|
| `feat`     | `enhancement`     |
| `fix`      | `bug`             |
| `docs`     | `documentation`   |
| `style`    | `style`           |
| `refactor` | `refactor`        |
| `perf`     | `performance`     |
| `test`     | `test`            |
| `build`    | `build`           |
| `ci`       | `ci`              |
| `chore`    | `chore`           |
| `revert`   | `revert`          |

- Si la etiqueta no existe todavía en el repositorio, créala antes de asignarla (`gh label create "<label>"`) o, si no es posible, informa al usuario para que la cree.
- Puedes añadir etiquetas extra si aportan contexto (ej. `triage`, un scope), pero la etiqueta derivada del `type` **siempre** debe estar presente.

## Auto-asignación

Todo issue creado se **auto-asigna a quien lo crea** (`@me`) por defecto, salvo que el usuario indique otro responsable.

## Cómo crear el issue

Prioriza **GitHub CLI**:

```bash
gh issue create \
  --title "[<emoji> <type>]: <subject>" \
  --body "<cuerpo con User Story + Descripción + Criterios de aceptación>" \
  --label "<label-del-type>" \
  --assignee "@me"
```

Ejemplo:

```bash
gh issue create \
  --title "[🐛 fix]: el scraper del BCV lanza timeout al hacer scraping" \
  --body "## User Story

Como usuario, quiero que la tasa del BCV se actualice sin errores, para consultar el tipo de cambio oficial del día de forma confiable.

## Descripción

El endpoint de scraping del BCV lanza un timeout cuando la página oficial tarda en responder...

## Criterios de aceptación
- El scraper reintenta ante un timeout antes de fallar.
- El endpoint nunca devuelve un 500 por un timeout del origen." \
  --label "bug" \
  --assignee "@me"
```

Si `gh` no está disponible, usa el conector MCP de GitHub si existe; si tampoco, informa al usuario que debe crear el issue manualmente respetando este formato.

## Notas

- El `type` del issue debe ser coherente con el `tipo` de la rama que luego lo respalde (`branch-naming.md`), el `type` de los commits (`commit-convention.md`) y el título de la PR (`pull-request.md`).
- ⚠️ **Relación con `branch-naming.md`**: esa regla define un caso específico — el *issue que respalda una rama*, cuyo **título es exactamente el nombre de la rama** (ej. `feat/DT-014`) y cuyo cuerpo lleva objetivo + criterios de aceptación. Esta regla (`issue-convention.md`) define el formato **general** de issues con título descriptivo. Si un mismo issue cumple ambos roles, decide con el usuario cuál título usar; no mezcles ambos formatos en un mismo título.
