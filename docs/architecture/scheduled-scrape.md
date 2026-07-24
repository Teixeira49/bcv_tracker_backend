# Cron de actualización de fuentes (Scheduled Scrape)

> Issue #72. Cron que refresca en BD **todas** las fuentes varias veces al día,
> llamando a `PUT /api/v1/venezuela/update-currencies` con el **Body por mercado**
> (#71).

## Decisión: GitHub Actions vs Vercel Cron → **GitHub Actions**

| Criterio | GitHub Actions (elegido) | Vercel Cron |
|---|---|---|
| Estado actual | Ya existe y funciona | Habría que crearlo |
| Costo | Gratis para este uso | Sujeto al plan de Vercel |
| Neutralidad de hosting | Independiente del hosting | Atado al proyecto de Vercel |
| Visibilidad de fallos | Job en rojo + logs en el repo | Logs en el dashboard de Vercel |
| Secretos | GitHub Secrets | Env de Vercel |

Se mantiene **GitHub Actions** (`.github/workflows/main.yml`): mínimo riesgo, ya
integrado, auditable desde el repo y con fallo visible. Si el proyecto se
consolidara 100% en Vercel, `vercel.json → crons` sería una alternativa directa
(golpea el mismo endpoint en horario); queda documentada como opción futura.

## Fuentes y modos (Body #71)

En cada corrida se envía el Body por mercado:

- **P2P cripto** (Binance, Bybit, OKX, Bitget): `ambas` (persiste buy y sell).
- **Fiat / agregadores** (Yadio, Airtm, DolarAPI): `todas`.
- **Exchange Monitor**: `own+monitor` (valor propio + promedio).
- **BCV**: `todas`, **solo** en la corrida de la medianoche de Venezuela.

## Cadencia

Seis corridas diarias (UTC): `04:00, 07:00, 11:00, 14:45, 18:15, 23:00`. Las
fuentes P2P/agregadores se refrescan en **todas**; el **BCV** solo se incluye en
la corrida de las **04:00 UTC**, que equivale a la **medianoche (00:00) en
Venezuela** (UTC-4). La cadencia es configurable editando la lista `schedule`
del workflow. Además, `workflow_dispatch` permite corridas manuales.

## Autenticación (#13)

El endpoint de escritura aún no está protegido (#13, abierto). El workflow ya
está **listo**: si el secreto `UPDATE_API_KEY` está definido, se envía como
`Authorization: Bearer <key>`; si no, la llamada va sin cabecera. Cuando #13
proteja el endpoint, basta definir el secreto en el repo — sin cambios en el
workflow.

## Fallo visible

El job hace `curl` con captura del código HTTP: cualquier respuesta **no-2xx**
imprime el cuerpo de la respuesta y hace `exit 1` (job en rojo), de modo que un
fallo de una fuente o del endpoint no pase desapercibido.

## Secretos requeridos

- `BACKEND_BASE_URL`: base del backend desplegado (sin barra final).
- `UPDATE_API_KEY` (opcional, hasta #13): API key de escritura.
