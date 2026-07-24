# Release Notes - v2.1.1 🧹
**DolarTracker Backend: The Maintainability & Foundations Update**
*Fecha de lanzamiento: 24 de Julio de 2026*

---

## 💎 Visión General

La versión **2.1.1** no añade fuentes ni cambia el contrato de la API: es un
release **de mantenibilidad y cimientos**. Salda la deuda técnica acumulada tras
*The Multi-Source Update* atacando siete frentes —concurrencia, contrato de
respuesta, gestión de esquema, cobertura de tests, duplicación y código
muerto— y deja **guardrails** para que esa deuda no vuelva a crecer. Es un
release **no-breaking**: el comportamiento observable de las fuentes existentes
se mantiene.

---

## 🛡️ Robustez y concurrencia

*   **Lectura de BD sin bloquear el event loop (#15)**: `getSavedCurrencies`
    ejecutaba `session.query(...)` síncrono directamente dentro de un `async def`.
    Ahora la lectura corre en un hilo vía `run_in_executor`, en línea con el
    resto de accesos a BD del service (`save_*_async`, `calculate_live_changes`).
*   **Contrato de respuesta garantizado (#18)**: los endpoints declaraban
    `response_model=BaseResponse[...]` pero devolvían un `Response` crudo, así que
    FastAPI **no validaba ni filtraba** la salida (drift doc vs realidad). Ahora
    devuelven el envelope tipado para que FastAPI serialice/valide contra el
    `response_model` declarado.

---

## 🗄️ Gestión de esquema

*   **`init_db` una sola vez, no por request (#19)**: se movió la creación de
    tablas al arranque en vez de invocarla en cada operación de escritura.
*   **Alembic adoptado de verdad (#19)**: se incorpora la configuración de
    migraciones (antes prometida en el README pero inexistente) con la migración
    inicial del esquema, y el README describe con precisión cómo se
    inicializa/migra.

---

## ✅ Tests y calidad

*   **Suite de tests del proyecto (#20)**: parseo del HTML del BCV con fixtures
    grabados, mapeo de JSON de Yadio y Binance, y endpoints vía
    `httpx.MockTransport` (incluyendo casos de error). Los tests corren en **CI
    en cada PR**.
*   **DRY: fetch y ROC centralizados (#21)**: se unifica el fetch por fuente
    (raw vs serializado), el bloque de las 4 tareas de Binance vive en un solo
    método y el cálculo de ROC se centraliza en un helper único.
*   **Código muerto eliminado (#22)**: `FilterParams`, la clase `BcvCurrency`,
    `Helper.validateDate`, `reset_db` y la línea comentada de `save_currencies_to_db`,
    sin dejar imports huérfanos.

---

## 🔒 Higiene del repositorio

*   **La base de datos SQLite deja de versionarse (#17)**: `api/data/bcv.db`
    (artefacto muerto; la app usa PostgreSQL vía `DATABASE_URL`) se saca del
    control de versiones y se ignora el patrón correspondiente en `.gitignore`.

---

## 🤖 Guardrails para el futuro

Para que la deuda saldada no reaparezca, este release deja mecanismos activos:

*   **CI** que corre `pytest` en cada PR.
*   **Reglas de tooling** que exigen tests para cada endpoint/fuente nueva,
    coherencia entre la salida y el `response_model` declarado, y el flujo de
    migraciones con Alembic.
*   **Auto-asignación de autor y labels por tipo** en cada PR (tooling de flujo).

---

## 🚀 Próximos Pasos
*   Caché en memoria (TTL) para las tasas en vivo.
*   Autenticación para los endpoints de escritura.
*   Persistencia de histórico real (serie temporal).

---
*DolarTracker - Monitorizando la economía con precisión y elegancia.*
