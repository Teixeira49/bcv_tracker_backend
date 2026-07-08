---
description: Versionado SemVer del proyecto, creación de GitHub Releases y mantenimiento del CHANGELOG a partir de un PR aprobado y mergeado. Aplica cada vez que se vaya a lanzar una versión nueva del proyecto.
---

# Versionado y Releases

Esta regla define cómo se versiona el proyecto (SemVer), cómo se crea el **GitHub Release** de cada versión y cómo se mantiene el **CHANGELOG**. Todo esto se dispara **solo** cuando un feature ya está en un **PR aprobado, cerrado y mergeado**: el usuario indicará "trae el PR #N" (o su URL) y a partir de ese PR real se documentan los cambios para constatar que se hicieron.

## Cuándo se dispara

- **Únicamente** cuando el usuario pide lanzar una versión a partir de un PR que ya está **mergeado**.
- Nunca se lanza una versión desde código sin mergear, desde un PR abierto o rechazado, ni por iniciativa propia.
- El PR es la **fuente de verdad**: la versión, el release note y la entrada del CHANGELOG se redactan a partir de lo que ese PR realmente cambió.

## Paso 0 — Leer la configuración

Lee `.claude/pr-config.json` (misma fuente que `pull-request.md`). De ahí se usan:

- `triggerMode`: nivel de disparo (`"manual"` | `"ask"` | `"auto"`) — gobierna la **publicación del GitHub Release** (ver Paso 5).
- `productionBranch`: rama de producción; es el **target del tag** del release. Por defecto `main`.

Si el archivo no existe, asume `triggerMode: "manual"` y `productionBranch: "main"`.

## Paso 1 — Traer y validar el PR mergeado

Con el número/URL que dio el usuario, trae el PR y **verifica** que cumple las condiciones antes de documentar nada:

```bash
gh pr view <N> --json number,title,body,state,mergedAt,mergeCommit,labels,reviewDecision,url,headRefName
```

Debe cumplirse:

- `state` = `MERGED` (cerrado **y** mergeado — un PR solo cerrado sin merge **no** cuenta).
- `reviewDecision` = `APPROVED` (aprobado).

Si alguna condición no se cumple, **detente** e informa al usuario; no crees release ni toques el CHANGELOG.

De `body`, `title`, `labels`, `headRefName` (tipo de la rama) y los commits del PR sale el material para la versión, el release note y el CHANGELOG. Para el detalle de cambios:

```bash
gh pr view <N> --json commits --jq '.commits[].messageHeadline'
```

Si `gh` no está disponible, usa el conector MCP de GitHub si existe; si tampoco, pídele al usuario que pegue el título, cuerpo, estado (mergeado/aprobado) y commits del PR.

## Paso 2 — SemVer: determinar la versión

El proyecto usa **Semantic Versioning**: `MAJOR.MINOR.PATCH` (tags con prefijo `v`, ej. `v1.1.1`).

Regla de incremento, coherente con `commit-convention.md`:

| Cambio predominante del PR | Parte que sube | Ejemplo |
|---|---|---|
| Breaking change (`!` o footer `BREAKING CHANGE:`) | **MAJOR** (`X`.0.0) | `v1.1.1` → `v2.0.0` |
| `feat` (nueva funcionalidad, no-breaking) | **MINOR** (`x.Y`.0) | `v1.1.1` → `v1.2.0` |
| `fix`, `perf`, `refactor`, `docs`, `build`, `chore`, etc. | **PATCH** (`x.y.Z`) | `v1.1.1` → `v1.1.2` |

Procedimiento:

1. Obtén la última versión publicada:
   ```bash
   git tag --sort=-v:refname | head -n1        # o: gh release list
   ```
2. Calcula la versión siguiente según la tabla (usa el cambio de mayor peso si el PR mezcla varios tipos).
3. **Confirma con el usuario** el número propuesto **siempre**, antes de crear archivos o el release:
   ```
   💡 Versión propuesta: vX.Y.Z (desde vA.B.C, por <feat|fix|breaking> del PR #N)
   ```
   Si el usuario indica otro número, úsalo. La confirmación de la versión es un gate obligatorio incluso en `triggerMode: auto`; lo que `auto` automatiza es la publicación del release, no la elección de la versión.

## Paso 3 — Escribir el release note en `docs/release/`

Siempre generas un markdown con las notas del release y lo guardas en:

```
docs/release/RELEASE_v<X.Y.Z>.md
```

Usa como referencia de tono y estructura `docs/release/RELEASE_v1.1.1.md`. Secciones:

**Obligatorias**
- **Título** con versión y emoji + subtítulo del release (ej. `# Release Notes - v1.2.0 🚀`).
- **Fecha de lanzamiento**: la fecha de merge del PR (`mergedAt`), en formato `DD de Mes de AAAA` (español).
- **Visión General**: resumen en prosa de lo que aporta la versión.
- **Registro de Cambios**: los cambios reales del PR, agrupados por categoría (UI/UX, Ingeniería/Estructura, Documentación, etc.), en viñetas. Deriva de los commits y del cuerpo del PR.

**Opcionales** (inclúyelas solo si aplican al cambio; no rellenes de más)
- **Evolución de la Arquitectura**: tabla comparativa y/o diagramas Mermaid (antes/después) cuando el cambio sea estructural.
- **Comparativa Visual**: tablas side-by-side de imágenes cuando haya cambios visibles de UI.
- **Próximos Pasos**: roadmap breve.

Cierra con la línea de firma del proyecto (ej. `*DolarTracker - Monitorizando la economía con precisión y elegancia.*`).

## Paso 4 — Actualizar el `CHANGELOG.md`

El `CHANGELOG.md` sigue el formato **[Keep a Changelog](https://keepachangelog.com/)** emparejado con SemVer. Agrega una entrada **nueva y concisa** para la versión (no dupliques todo el release note; el detalle vive en `docs/release/`).

- Si el archivo está vacío o no tiene cabecera, inicialízalo:
  ```markdown
  # Changelog

  Todos los cambios notables de este proyecto se documentan en este archivo.

  El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
  y el proyecto sigue [Semantic Versioning](https://semver.org/lang/es/).
  ```
- Inserta la versión nueva **arriba** (orden descendente, la más reciente primero):
  ```markdown
  ## [X.Y.Z] - AAAA-MM-DD

  ### Added
  - <lo nuevo agregado>

  ### Changed
  - <cambios en funcionalidad existente>

  ### Fixed
  - <bugs corregidos>

  ### Removed
  - <lo que se eliminó>
  ```
- Usa la fecha de merge del PR (`AAAA-MM-DD`). Incluye solo las subsecciones (`Added`, `Changed`, `Fixed`, `Removed`, `Deprecated`, `Security`) que apliquen; omite las vacías.
- Al final del archivo, mantén los enlaces de comparación por versión cuando sea posible:
  ```markdown
  [X.Y.Z]: https://github.com/<owner>/<repo>/compare/vA.B.C...vX.Y.Z
  ```

## Paso 5 — Crear el GitHub Release (según `triggerMode`)

El release usa el tag `vX.Y.Z` sobre `productionBranch` y su cuerpo es el markdown de `docs/release/`.

Comando base (prioriza GitHub CLI):

```bash
gh release create v<X.Y.Z> \
  --target <productionBranch> \
  --title "v<X.Y.Z> - <subtítulo del release>" \
  --notes-file docs/release/RELEASE_v<X.Y.Z>.md
```

Comportamiento por modo:

### `manual`
Escribe el release note (Paso 3) y actualiza el CHANGELOG (Paso 4), pero **no** crea el release en GitHub. Informa las rutas de los archivos generados y termina. No hagas push de tags ni publiques nada.

### `ask`
1. Muestra en el chat: la **versión** confirmada, el **contenido** del release note, la **entrada** del CHANGELOG y el **tag/target**.
2. Espera aprobación **escrita** del usuario.
3. Tras aprobar, crea el release **publicado** con el comando de arriba.

### `auto`
Crea el release **publicado** directamente con el comando de arriba (la versión ya fue confirmada en el Paso 2). Registra en el chat el tag y la URL resultante.

> Nota de seguridad: crear/publicar un GitHub Release es una acción que publica contenido. En `auto` está pre-autorizada por esta configuración; en `ask` requiere tu visto bueno explícito; en `manual` no se publica.

Si `gh` no está disponible, usa el conector MCP de GitHub si existe; si tampoco, deja los archivos escritos (como en `manual`) e informa que el release debe crearse manualmente. Tras crearlo, devuelve la URL del release.

## Notas

- Un release = una versión = un tag `vX.Y.Z`. No reutilices tags existentes; si el tag ya existe, detente y avisa.
- El `type` predominante del PR (y de la rama, `branch-naming.md`) debe ser coherente con el incremento SemVer elegido.
- El nombre del archivo de release siempre lleva el prefijo `v` y la versión completa: `RELEASE_v<X.Y.Z>.md`.
- El CHANGELOG es el resumen navegable; el release note en `docs/release/` es el documento extenso. Mantén ambos consistentes con lo que el PR realmente cambió.
