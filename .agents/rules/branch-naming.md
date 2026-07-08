---
description: Nomenclatura de ramas de git y su issue de GitHub asociado. Aplica cada vez que se vaya a crear una rama nueva en este repositorio.
---

# Nomenclatura de Ramas

Este proyecto no usa Jira: el ID de cada rama lo genera y lleva la cuenta el propio repositorio (no un ticket externo). Cada rama se vincula a un issue de GitHub, pero **el nombre de la rama no depende del issue** ni al revés (ver "Vínculo con el issue de GitHub" más abajo).

## Paso 0 — Leer la configuración

Antes de crear una rama, lee `.claude/pr-config.json` si existe. Usa:

- `baseBranch`: rama base por defecto para todo lo que no sea hotfix. Por defecto `development`.
- `productionBranch`: rama de producción de la que salen los hotfixes. Por defecto `main`.
- `branchProjectCode`: iniciales del proyecto para el ID de rama. Por defecto `DT` (DolarTracker).

Si el archivo no existe, asume esos mismos valores por defecto. En este repositorio el archivo ya existe en `.claude/pr-config.json` con `branchProjectCode: "DT"`, `baseBranch: "development"` y `productionBranch: "main"`.

> Nota: al momento de escribir esta regla el repo aún no tiene rama `development` (solo `main`). Si no existe cuando la necesites, avisa al usuario antes de crearla — no la crees por tu cuenta sin confirmar.

## Base de la rama

- **Hotfix**: se saca **directamente de producción** (`productionBranch`).
- **Todo lo demás** (`fix`, `feat`, etc.): se saca de `baseBranch` (`development`).

```bash
git checkout <base>
git pull
git checkout -b <nombre-de-rama>
```

Donde `<base>` es `productionBranch` para hotfix, o `baseBranch` en cualquier otro caso.

## Nomenclatura

```
<tipo>/<branchProjectCode>-<numero>
```

- **tipo**: `feat`, `fix`, `hotfix`, `refactor`, `docs`, `chore`, `build`, `test`, etc. (en minúsculas), coherente con `commit-convention.md`.
- **branchProjectCode**: iniciales del proyecto, ej. `DT`.
- **numero**: ID secuencial de **una sola serie compartida entre todos los tipos** (no hay una numeración separada para `feat` vs `fix`), con al menos 3 dígitos: `001`, `002`, ... `010`, ... `999`, `1000`...

Ejemplos:
```
feat/DT-001
fix/DT-002
feat/DT-014
```

## Cómo obtener el siguiente número

Antes de crear una rama, calcula el ID más alto ya usado (local y remoto) y usa el siguiente:

```bash
git branch --list "*/${CODE}-*"
git ls-remote --heads origin | grep -E "${CODE}-[0-9]+"
```

Extrae el número de cada nombre encontrado (`<tipo>/<CODE>-<numero>`), toma el máximo de todos (sin importar el tipo) y súmale 1. Si no hay ninguna rama previa con ese código, empieza en `001`.

## Vínculo con el issue de GitHub

Cada rama debe estar respaldada por un issue de GitHub, pero el vínculo **no se hace por el nombre** (ni el issue se titula como la rama, ni la rama incluye el título del issue). El issue se crea con su propio formato descriptivo (ver `issue-convention.md`) y la relación issue↔rama se establece con el mecanismo nativo de GitHub: **linked branches** (sección *Development* del issue).

### Mecanismo recomendado: `gh issue develop`

GitHub registra el vínculo issue↔rama en su base de datos (aparece en la sección *Development* del issue), independientemente de cómo se llame la rama. La forma más directa de crearlo es con la CLI:

```bash
gh issue develop <numero-issue> --name "<nombre-de-rama>" --base <base> --checkout
```

- `<numero-issue>`: el número del issue de GitHub (ej. `42`), **no** el ID interno `DT-###`.
- `--name`: el nombre de rama según la nomenclatura de arriba (`<tipo>/<branchProjectCode>-<numero>`). Si se omite, GitHub genera uno a partir del título del issue.
- `--base`: `productionBranch` para hotfix, o `baseBranch` en cualquier otro caso.
- `--checkout`: cambia a la rama recién creada.

Esto crea la rama, la vincula al issue y la deja lista para trabajar en un solo paso.

### Procedimiento

1. Asegúrate de que exista el issue (créalo con `issue-convention.md` si aún no existe; si falta el objetivo y los criterios de aceptación, pídeselos al usuario).
2. Determina el `<nombre-de-rama>` según la nomenclatura de arriba y la `<base>` correcta.
3. Crea y vincula la rama:
   ```bash
   git checkout <base> && git pull
   gh issue develop <numero-issue> --name "<nombre-de-rama>" --base <base> --checkout
   ```
4. Al abrir la PR desde esa rama (`gh pr create`), el vínculo se propaga y la PR queda enlazada al issue automáticamente.

### Refuerzo con keywords de cierre

Para que el issue se **cierre solo** al mergear, incluye en el cuerpo o los commits de la PR una keyword de cierre referenciando el número del issue:

```
Closes #42
```

Keywords válidas: `close`/`closes`/`closed`, `fix`/`fixes`/`fixed`, `resolve`/`resolves`/`resolved`. Solo surten efecto cuando la PR apunta a la rama por defecto del repositorio.

### Si `gh` no está disponible

Usa el conector MCP de GitHub si existe. Si tampoco, crea la rama con `git checkout -b <nombre-de-rama>` y vincúlala manualmente desde la sección *Development* del issue en la web; avisa al usuario que debe hacer ese enlace para no perder la trazabilidad.

## Notas

- El `tipo` de rama debe ser coherente con el `type` del issue (`issue-convention.md`), de los commits (`commit-convention.md`) y del título de la PR (`pull-request.md`).
- No incluyas texto descriptivo en el nombre de la rama: solo `<tipo>/<branchProjectCode>-<numero>`. El objetivo, la User Story y los criterios de aceptación viven en el issue (`issue-convention.md`), no en el nombre de la rama.
- El ID interno `DT-###` identifica la rama dentro del repo; el vínculo formal con el issue lo maneja GitHub (linked branch), no el nombre.
