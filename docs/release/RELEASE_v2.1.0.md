# Release Notes - v2.1.0 🚀
**DolarTracker Backend: The Multi-Source Update**
*Fecha de lanzamiento: 22 de Julio de 2026*

---

## 💎 Visión General

La versión **2.1.0** multiplica las fuentes de tasas del proyecto: pasa de 3
mercados paralelos a **8 fuentes** (BCV oficial + 7 paralelas/cripto), todas
sobre endpoints públicos sin autenticación y siguiendo el mismo patrón. Además
completa el ciclo de persistencia (todas las fuentes se pueden **guardar** y
**releer** desde la base de datos) y endurece la robustez de red. Es un release
**aditivo y no-breaking**: no cambia el contrato de las fuentes existentes.

---

## ✨ Nuevas fuentes de tasa

Se integran **seis** plataformas nuevas, cada una con su endpoint propio (`/…`)
y su variante `/averaged` cuando aplica:

*   **Bybit P2P** (USDT/USDC, compra/venta) — con degradación elegante por par.
*   **OKX P2P** (USDT/USDC).
*   **Bitget P2P** (USDT/USDC).
*   **Airtm** (compra/venta del dólar USD/VES) + endpoint `/airtm/averaged`.
*   **DolarAPI** (agregador del dólar oficial y paralelo).
*   **Exchange Monitor** (agregador de mercados) — resuelto con **scraping
    híbrido**: token CSRF del HTML + endpoint de datos JSON, ya que el sitio
    renderiza las tasas por JavaScript. Persiste su valor propio y el promedio
    estimado.

Junto a las ya existentes (**BCV**, **Yadio**, **Binance P2P**), el sistema
consolida **8 fuentes**.

---

## 🗄️ Persistencia y consulta homogéneas

*   **`PUT /update-currencies`** y **`GET /saved-currencies`** aceptan ahora
    todas las fuentes como activadores independientes (BCV, Yadio, Binance,
    Bybit, OKX, Bitget, Airtm, DolarAPI, Exchange Monitor). Todas hacen el ciclo
    completo *guardar ↔ releer* desde la BD.
*   **Filtros `enforce` independientes para Exchange Monitor** en
    `saved-currencies`: `enforce_em_own` (solo "Exchange Monitor") y
    `enforce_em_average` (solo "Monitor Dólar").
*   Refactor interno de `update-currencies` a una tabla de fuentes emparejada
    con `zip` (elimina el conteo de índices frágil; sin cambio de comportamiento).

---

## 🛡️ Robustez

*   **Bitget · anti-429**: sus 4 pares se piden **en serie** (no en ráfaga) y
    cada request **reintenta ante 429** con backoff exponencial (respetando
    `Retry-After`). El burst concurrente era lo que gatillaba el rate limit.
*   **Parseo JSON tolerante** en `HttpClient` (`strict=False`): evita que un
    carácter de control crudo en el texto de un anuncio P2P tumbe la fuente.

---

## 🛠️ Ingeniería, Proceso y Documentación

*   **`.env.example`** con todas las variables requeridas + validación fail-fast
    al arranque documentada.
*   Nuevas reglas de tooling: **`environment-variables`** (sincronizar
    `.env.example`/`_REQUIRED_ENV`/README al tocar env vars) y
    **`documentation-convention`**.
*   Docstrings de servicios/endpoints y metadata OpenAPI al día con las fuentes.
*   Carpeta **`design/`** con los design tokens de marca (`themeV2.json`).

---

## ⚙️ Notas de despliegue

Este release añade fuentes cuyas URLs se configuran por entorno
(`MARKET_DATA_PROVIDER_*_URL`, slots C–H). Como la validación es fail-fast,
**todas deben existir en el entorno de producción antes de desplegar** o la app
no arranca. (Ya aprovisionadas en Vercel.)

---

## 🚀 Próximos Pasos
*   Caché en memoria (TTL) para las tasas en vivo.
*   Autenticación para los endpoints de escritura.
*   Persistencia de histórico real (serie temporal).

---
*DolarTracker - Monitorizando la economía con precisión y elegancia.*
