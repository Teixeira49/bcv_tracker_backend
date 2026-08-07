# Release Notes - v3.1.0 🩺
**DolarTracker Backend: The Data Integrity Update**
*Fecha de lanzamiento: 7 de Agosto de 2026*

---

## 💎 Visión General

La versión **3.1.0** no agrega fuentes ni endpoints: repara la **integridad de los
datos que ya se estaban recolectando**. Doce de las veinte monedas de la base
llevaban entre 11 y 15 días sin actualizarse en la API, aunque el cron corría
correctamente seis veces al día y devolvía `200` en cada corrida.

La causa no era una sola. Eran tres defectos independientes que se tapaban entre
sí: una clave de negocio incompleta que hacía que las series de una misma moneda
se pisaran al guardar, filas huérfanas que se escribían por un lado y se leían
por otro, y una condición del cron que dependía del reloj del runner en vez del
horario programado.

El release corrige los tres, con una migración de datos que **no borra ninguna
fila**: las huérfanas se reutilizan como la serie que faltaba.

---

## 🔍 Los tres defectos

### 1. El lado de la operación no formaba parte de ninguna clave

La identidad de una cotización era `(code, platform)`, pero el lado del libro
viajaba **dentro del nombre** (`"Tether-Buy"`), que no forma parte de ninguna
clave. Como cada fuente manda todas sus series en el mismo lote, la segunda
escritura pisaba a la primera.

Se veía en los datos: **todas** las filas cripto acabaron con nombre `*-sell`,
las dos de Airtm como `Dolar-sell` y las dos de DolarAPI como `Paralelo`. El
dólar **oficial** de DolarAPI y el lado de **compra** de las cinco fuentes con
libro nunca sobrevivían a su propia corrida. El `change` de esas filas tampoco
era una variación temporal: era el spread entre las dos series.

### 2. Se escribía en una fila y se leía de otra

Existían filas **gemelas** por `(code, platform)`, nacidas en la primera corrida
de cada fuente: con `autoflush=False`, ninguna de las dos inserciones del lote
veía a la otra, y ambas entraban como filas nuevas.

A partir de ahí, el upsert actualizaba siempre la de `id` más bajo, mientras la
lectura hacía `max(id)` agrupado. Es decir: la API servía justo la gemela que
nadie estaba actualizando. El dato fresco se escribía cada tres horas y nunca se
leía.

### 3. El BCV nunca entraba al cron

La inclusión del BCV se decidía con `date -u +%H` = `"04"`, la hora a la que el
runner **arrancaba**. GitHub Actions encola los crons de los repos gratuitos y
los arranca con retrasos de una a tres horas: el de las 04:00 UTC llegó a
arrancar a las 06:34, el de las 11:00 a las 12:55. La comparación casi nunca se
cumplía.

Resultado: entre el 2026-07-24 —cuando el disparador se movió a la hora `04`— y
el 2026-08-07, **ninguna** de las corridas incluyó el BCV.

---

## 📋 Registro de Cambios

### Base de datos y modelo

*   Nueva columna **`variant`** en `currencies`: identifica la serie de la
    cotización dentro de `(code, platform)`.
*   La **clave de negocio** pasa a ser `(code, platform, variant)`, con
    `UNIQUE (code, platform, variant)` haciéndola cumplir en la base.
*   `variant` es **NOT NULL con centinela `'na'`**, no nullable: PostgreSQL y
    SQLite tratan los `NULL` como distintos entre sí dentro de un índice único,
    así que una columna nullable no habría impedido los duplicados.
*   Migración **`0002_add_currency_variant`** con backfill de datos: deduce la
    serie del nombre de cada fila y, donde hay gemelas, la de `id` más bajo
    conserva la suya y la huérfana **estrena la complementaria**. Ninguna fila se
    borra. La gemela adopta además el valor vigente de su hermana, para que el
    primer ROC no se calcule contra un valor congelado.

### Fuentes

*   Binance, Bybit, OKX y Bitget etiquetan cada par como `buy` o `sell`.
*   Airtm separa `buy` (`addValue`) de `sell` (`withdrawValue`).
*   DolarAPI deriva la variante del campo `fuente` del payload, así que el
    **dólar oficial** vuelve a tener fila propia junto al paralelo — y una fuente
    nueva de DolarAPI estrenaría la suya en vez de pisar a otra.
*   Los modos promedio guardan su resultado como serie `average`, sin
    sobrescribir la compra ni la venta que lo originan.

### Corrección de lecturas

*   `calculate_live_changes` cruza por variante: la compra ya no calcula su ROC
    contra la venta guardada.
*   `_query_latest_rows` pierde la subconsulta `max(id)`, obsoleta con el `UNIQUE`
    nuevo — y que era justamente la que servía la gemela congelada.

### Infraestructura

*   El cron decide la inclusión del BCV por **`github.event.schedule`** (el cron
    literal que disparó la corrida, inmune al retraso de encolado) en vez de la
    hora del reloj.
*   Nuevo input **`include_bcv`** en `workflow_dispatch`, para refrescar el BCV
    fuera de su horario.

### API

*   `CurrencySchema` expone **`variant`** como campo opcional.

### Documentación

*   `docs/architecture/scheduled-scrape.md` documenta cómo se decide incluir el
    BCV y por qué no puede depender del reloj.

---

## 🔄 Evolución del modelo de datos

| | Antes (v3.0.0) | Ahora (v3.1.0) |
|---|---|---|
| Identidad de una cotización | `(code, platform)` | `(code, platform, variant)` |
| Lado de la operación | dentro del `name` (`"Tether-Buy"`) | columna `variant` |
| Garantía en la BD | ninguna | `UNIQUE (code, platform, variant)` |
| Series por moneda que sobreviven | 1 (la última escrita) | todas |
| Significado del `change` en fuentes con dos lados | spread compra/venta | variación contra la corrida anterior |
| Filas servidas por la lectura | `max(id)` por `(code, platform)` | la fila única de cada clave |

---

## ⚠️ Notas de actualización

**La migración va antes que el despliegue del código.** El ORM ya selecciona la
columna `variant`; si el deploy llega primero, toda consulta a `currencies`
falla. La migración sí es compatible hacia atrás con el código anterior, así que
aplicarla antes es seguro:

```bash
alembic upgrade head
```

> En instalaciones cuyo esquema haya nacido del `create_all()` del arranque y no
> de Alembic, no existe la tabla `alembic_version` y hay que marcar la línea base
> antes: `alembic stamp 0001_initial_schema`.

Dos efectos esperados y acotados:

*   **Un ciclo con `change` distorsionado** en las filas reutilizadas: heredan el
    valor de su gemela, así que el primer ROC tras la migración es la diferencia
    entre series. Se corrige solo en la segunda corrida.
*   **Una misma moneda puede venir más de una vez** en `saved-currencies` con
    modo `ambas`, una por serie. Es lo que ese modo siempre significó, pero hasta
    ahora no se cumplía. El schema sigue siendo compatible (`variant` es aditivo
    y opcional); revisa a los clientes que asuman una sola entrada por `code`.

---

## 🔭 Próximos Pasos

*   Normalizar la moneda en tabla propia referenciada por FK: la mitad que queda
    del issue #73.
*   `update_from_selection` usa `asyncio.gather` sin `return_exceptions`: una
    sola fuente caída aborta la corrida completa y no persiste nada, ni siquiera
    las fuentes que sí respondieron.
*   Persistencia de histórico real (serie temporal), ahora que cada serie tiene
    identidad propia.

---
*DolarTracker - Monitorizando la economía con precisión y elegancia.*
