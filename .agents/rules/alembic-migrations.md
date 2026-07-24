---
description: Convenciones obligatorias para crear, revisar y ejecutar migraciones de Alembic en este repositorio. Aplica cada vez que se cambie el esquema de la BD (modelos ORM, tablas, columnas, constraints, índices) o se necesite generar/aplicar una migración. Pensada para que un agente pueda ejecutarla de forma autónoma y segura.
---
# Migraciones de Base de Datos (Alembic)

El esquema versionado de la base de datos lo gobierna **Alembic** (adoptado en DT-021, issue #19). La configuración vive en `alembic.ini` y las migraciones en `migrations/`; la línea base es `migrations/versions/0001_initial_schema.py` (tablas `currencies` y `platform_dates`).

Esta regla define **cómo** se crea, revisa y ejecuta una migración, qué está y qué **no** está permitido, y el **orden de ejecución**. Es la guía única para que cualquier persona —o un agente— toque el esquema sin romper la coherencia entre modelos ORM, migraciones y la BD real.

## Fuente de verdad y arquitectura

- Los **modelos ORM de SQLAlchemy** (`api/models/bd_currency.py`, heredan de `Base`) son la definición del esquema. `migrations/env.py` usa `Base.metadata` como `target_metadata` para el autogenerate.
- Alembic toma la URL de la BD de la variable de entorno **`DATABASE_URL`** (la misma que usa la app, `api/core/config`). **Nunca** se hardcodea en `alembic.ini` (no se versionan credenciales).
- `init_db()` (`create_all`) corre **una sola vez en el arranque** (`lifespan` de `api/main.py`) como garantía idempotente de que las tablas existan en entornos efímeros (serverless / cold start). **No sustituye** a las migraciones: Alembic es la fuente de verdad del esquema versionado.

## Cuándo aplica

Siempre que un cambio **agregue, elimine o modifique** una tabla, columna, tipo, constraint, índice o default en los modelos ORM (`Base`). Si el cambio no toca el esquema de la BD, esta regla no aplica.

## Cómo crear una migración (flujo obligatorio)

1. **Primero modifica el modelo ORM** en `api/models/bd_currency.py` (o el modelo correspondiente). El modelo es el punto de partida; la migración se deriva de él.
2. **Genera la migración con autogenerate** (no la escribas a mano salvo casos que autogenerate no cubre, ver más abajo):
   ```bash
   alembic revision --autogenerate -m "descripción breve en imperativo"
   ```
   `DATABASE_URL` debe apuntar a una BD **con el esquema anterior ya aplicado** (`alembic upgrade head` antes), para que el diff sea correcto.
3. **REVISA SIEMPRE el archivo generado** en `migrations/versions/`. Autogenerate no es infalible: no detecta bien renombres (los ve como drop+add), cambios de tipo server-side, `CHECK`/nombres de constraints, ni datos. Corrige el `upgrade()`/`downgrade()` a mano cuando haga falta.
4. **Escribe un `downgrade()` correcto** que revierta exactamente lo que hace `upgrade()`. Una migración sin downgrade real es deuda: solo se admite un downgrade vacío si la reversión es genuinamente imposible, y debe documentarse en el docstring.
5. **Verifica que la migración coincide con los modelos** (ver "Verificación").
6. **Sincroniza la documentación** del esquema en el mismo cambio (regla `database-schema-sync.md`: actualiza `docs/schema/SCHEMA.md`).

## Convenciones de nomenclatura y contenido

- **`revision` id**: prefijo numérico secuencial de 4 dígitos + `_` + descripción en `snake_case`: `0002_add_currency_source_column`. El archivo se nombra igual (`migrations/versions/0002_add_currency_source_column.py`). Mantiene el historial legible y ordenable (complementa el hash aleatorio por defecto de Alembic, que aquí no se usa como nombre).
- **`down_revision`**: apunta al `revision` id de la migración inmediatamente anterior. La línea base (`0001_initial_schema`) tiene `down_revision = None`.
- **Mensaje `-m`**: imperativo, en presente, coherente con `commit-convention.md` (ej. `"add source column to currencies"`).
- **Una migración = un cambio lógico de esquema.** No mezcles cambios no relacionados en la misma revisión.
- Usa siempre la API de `alembic.op` + `sqlalchemy` (`op.create_table`, `op.add_column`, `op.create_index`, ...); no ejecutes DDL crudo salvo que sea imprescindible (y entonces documenta por qué).

## Qué está permitido y qué NO

**Permitido:**
- Crear nuevas migraciones que avancen el esquema hacia adelante.
- Editar una migración **que aún no se ha mergeado ni aplicado en ningún entorno compartido** (todavía es tuya, local a la rama/PR).
- Escribir migraciones de datos (data migrations) cuando el cambio de esquema lo requiera, idealmente separadas de las de estructura.

**NO permitido:**
- **Editar o borrar una migración ya mergeada/aplicada** (en `development`, `main` o producción). El historial es inmutable: para corregir algo, crea una **nueva** migración que lo enmiende.
- **Dejar más de un `head`.** El historial debe ser **lineal** (una sola cabeza). Si un merge de ramas genera dos heads, resuélvelo con `alembic merge` en una migración de merge explícita antes de continuar.
- **Hardcodear `sqlalchemy.url`** en `alembic.ini` ni credenciales en las migraciones.
- **Sustituir migraciones por `create_all`/`init_db`** para cambios de esquema: `init_db` solo garantiza el arranque, no versiona cambios.
- **Commitear una migración sin revisar el autogenerate** ni sin `downgrade`.
- **Operaciones destructivas silenciosas** (drop de tabla/columna con datos) sin dejarlo explícito en el docstring de la migración y sin confirmación humana; un agente **debe detenerse y preguntar** antes de generar/aplicar un drop que pueda perder datos en un entorno con datos reales.
- **Aplicar migraciones contra producción de forma autónoma.** Un agente puede generar y aplicar migraciones en local/CI/preview, pero la aplicación en producción requiere aprobación humana.

## Orden de ejecución de las migraciones

- Alembic aplica las migraciones **en orden encadenado** siguiendo `down_revision` (de la más antigua a la más nueva). El historial es una lista enlazada con una sola cabeza (`head`).
- **Aplicar todo hacia adelante** (lo habitual, y lo que hace el onboarding del README):
  ```bash
  alembic upgrade head
  ```
- **Avanzar/retroceder de a pasos**:
  ```bash
  alembic upgrade +1        # una migración hacia adelante
  alembic downgrade -1      # una migración hacia atrás
  alembic downgrade base    # revierte todo hasta el estado vacío
  ```
- **Inspeccionar**:
  ```bash
  alembic current           # revisión aplicada actualmente en la BD
  alembic history --verbose # historial completo y su encadenamiento
  alembic heads             # debe devolver EXACTAMENTE una cabeza
  ```
- En **serverless**, además del `alembic upgrade head` del pipeline/manual, el `init_db()` del arranque garantiza que las tablas existan aunque el `upgrade` no se haya corrido aún; aun así, **el flujo correcto para cambios de esquema es la migración**, no depender del `create_all`.

## Verificación (obligatoria antes de commitear)

1. **Aplica y comprueba el diff contra los modelos** sobre una BD desechable:
   ```bash
   export DATABASE_URL="sqlite:////tmp/alembic_check.db"   # BD temporal
   alembic upgrade head
   alembic check    # debe imprimir "No new upgrade operations detected"
   ```
   Si `alembic check` detecta operaciones pendientes, la migración **no** refleja los modelos: complétala.
2. **`alembic heads` devuelve una sola cabeza.**
3. **`pytest` en verde.** El test `tests/test_db_init_and_migrations.py::test_alembic_migration_matches_models` corre exactamente este `upgrade head` + `check` como guardrail; toda migración nueva debe mantenerlo verde. Si agregas una tabla/columna, añade también su cobertura de comportamiento donde aplique.

## Relación con otras reglas

- `database-schema-sync.md`: tras la migración, actualiza `docs/schema/SCHEMA.md` (fuente semántica interna).
- `commit-convention.md`: los cambios de migración usan el tipo que corresponda (`refactor`/`feat`/`fix` según el cambio de esquema, o `build` si es solo tooling de Alembic).
