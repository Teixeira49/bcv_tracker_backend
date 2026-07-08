---
description: Mantiene sincronizado el esquema semántico interno docs/schema/SCHEMA.md con la base de datos real. Aplica cada vez que se cambie la BD (modelos ORM, tablas, columnas, constraints o lógica de escritura), y también cuando el archivo semántico aún no existe.
---
# Sincronización del esquema semántico de la BD

`docs/schema/SCHEMA.md` es la **ficha semántica interna** de la base de datos: describe tablas,
columnas, su significado de negocio, constraints y reglas de escritura. Sirve para que el agente
tome decisiones sin reconstruir el modelo desde cero. Debe reflejar **siempre** el estado real de
la BD. Esta regla define cómo mantenerlo.

> El archivo es **interno**: vive en `docs/schema/` y está en `.gitignore`. No se sube a
> producción ni al repositorio público, porque expone la estructura de datos.

## Fuente de verdad

- La estructura vigente son los **modelos ORM de SQLAlchemy** en `api/models/bd_currency.py`
  (heredan de `Base`), que es lo que `init_db()` crea en producción.
- La lógica de escritura/upsert vive en `api/services/bd_service.py`.
- El archivo local `api/data/bcv.db` (SQLite) puede estar **obsoleto**: no lo tomes como fuente
  de verdad sin contrastarlo contra los modelos ORM.

## Cuándo se dispara

Esta regla aplica **automáticamente**, sin que el usuario lo pida, siempre que ocurra alguna de estas:

1. **No existe `docs/schema/SCHEMA.md`** → lo PRIMERO es crearlo (ver Paso 0).
2. Se **añade, elimina o modifica** un modelo ORM (`Base`) o una tabla/columna/constraint/índice.
3. Cambia la **lógica de escritura** (upserts, claves de negocio, cálculo de campos derivados
   como `change`/ROC, defaults, `onupdate`).
4. Se toca la **conexión** (`DATABASE_URL`, motor, timezone de las fechas) de forma que afecte la
   estructura o el significado de los datos.
5. Cambia la relación entre modelos ORM y los schemas de respuesta (Pydantic) que altere el
   significado de una columna.

Si el cambio es puramente de negocio en código que **no** toca la BD, esta regla no aplica.

## Paso 0 — Si el archivo no existe: crearlo

Antes de cualquier otra cosa, comprueba si existe `docs/schema/SCHEMA.md`. Si **no** existe:

1. Crea la carpeta `docs/schema/` si hace falta.
2. Lee la BD (modelos ORM + lógica de `bd_service.py`; opcionalmente inspecciona la BD real con
   el engine/`inspect` de SQLAlchemy) y **genera el archivo desde cero** con la estructura de la
   sección "Contenido mínimo".
3. Verifica que `docs/schema/` esté en `.gitignore`; si no, añádelo.

## Pasos cuando ya existe y hubo un cambio en BD

1. **Releer la BD:** revisa los modelos ORM en `api/models/bd_currency.py` y la lógica de
   `api/services/bd_service.py`. Contrasta contra la BD real cuando sea posible.
2. **Diff mental:** identifica qué cambió respecto a lo documentado (tablas, columnas, tipos,
   constraints, índices, defaults, reglas de upsert, campos derivados).
3. **Actualizar `SCHEMA.md`:** modifica solo las secciones afectadas; mantén el significado
   semántico (no solo el tipo). Actualiza la fecha de "Última sincronización".
4. **Anotar discrepancias:** si la BD real difiere de los modelos ORM (p. ej. un `.db` obsoleto),
   déjalo escrito explícitamente en el archivo.
5. **No lo subas al repo público:** confirma que sigue ignorado por git.

## Contenido mínimo de `docs/schema/SCHEMA.md`

- Aviso de que es interno y no va a producción, y referencia a esta regla.
- Fecha de última sincronización y fuente de verdad.
- Conexión y motor (engine, `DATABASE_URL`, timezone de fechas, cómo se crean las tablas).
- Por cada tabla: nombre, modelo ORM, y una fila por columna con **tipo + constraints +
  significado semántico**.
- Reglas de escritura/upsert relevantes (clave de negocio, campos calculados como ROC/`change`).
- Valores de dominio conocidos (p. ej. los nombres válidos de `platform`).
- Un resumen de "decisiones rápidas" al final.

## Regla de oro

Si tocas la base de datos y **no** actualizas `docs/schema/SCHEMA.md`, el cambio está incompleto.
