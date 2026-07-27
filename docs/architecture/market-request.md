# Body por mercado y máquina de estados (update / saved-currencies)

> Issue #71. Reemplaza (breaking, **MAJOR**) los flags booleanos y `enforce_*`
> de `update-currencies` y `saved-currencies` por un **Body** estructurado con un
> estado (`mode`) por mercado. Absorbe la optimización SQL de lectura de #46.

## Endpoints

| Endpoint | Método | Body | Semántica del estado |
|---|---|---|---|
| `/api/v1/venezuela/update-currencies` | **PUT** | `MarketSelection` | qué se **persiste** (solo modos en vivo) |
| `/api/v1/venezuela/saved-currencies`  | **POST** | `MarketSelection` | qué se **lee/devuelve** (BD y/o en vivo) |

`saved-currencies` pasó de `GET` a **`POST`**: acepta un Body estructurado y
GET-con-body no es fiable entre clientes.

## Body

```json
{
  "markets": {
    "bcv": "bd-solo-dolar",
    "binance": "average",
    "exchange_monitor": "own+monitor"
  }
}
```

`markets` mapea cada mercado a su estado. **Un mercado no mencionado equivale a
`off`** (no se toca): explícito y predecible; agregar un mercado nuevo no altera
el comportamiento de requests existentes.

## Estados (máquina de estados por mercado)

| Estado | Fuente | Alcance |
|---|---|---|
| `off` | — | no se envía/persiste ni se lee |
| `solo-dolar` | en vivo | solo el dólar (USD) |
| `todas` | en vivo | todas sus divisas |
| `bd-solo-dolar` | BD | solo el dólar |
| `bd-todas` | BD | todas sus divisas |
| `average` | en vivo | [cripto] promedio por activo (buy+sell)/2 |
| `ambas` | en vivo | [cripto] ambos lados (buy y sell) |
| `own` | en vivo | [Exchange Monitor] solo su valor propio |
| `own+monitor` | en vivo | [Exchange Monitor] valor propio + promedio |

### Modos permitidos por mercado (validado con Pydantic)

| Mercado | Modos permitidos |
|---|---|
| bcv, yadio, airtm, dolarapi | `off`, `solo-dolar`, `todas`, `bd-solo-dolar`, `bd-todas` |
| binance, bybit, okx, bitget | `off`, `average`, `ambas`, `bd-todas` |
| exchange_monitor | `off`, `own`, `own+monitor`, `bd-todas` |

Un `(mercado, modo)` no admitido → **422** (validación del Body).

## Reglas por endpoint

- **update-currencies**: solo aplican los modos **en vivo** (persiste datos
  frescos). Un modo `bd-*` en el Body → **422** (no tiene sentido "persistir
  desde BD").
- **saved-currencies**: los modos `bd-*` leen de la BD; los modos en vivo hacen
  fetch y calculan el ROC contra la BD (integra el antiguo `fill_missing`).

## Lectura de BD optimizada (absorción de #46)

Las lecturas `bd-*` empujan a SQL (no filtran en Python tras traer todo):

- **Filtro por plataforma** en `WHERE`.
- **"Último por `(code, platform)`"**: subconsulta `max(id)` agrupada, que acota
  el resultado aunque la tabla crezca con histórico (#14). Con el upsert actual
  (una fila por `code+platform`) el resultado no cambia.
- **Solo-dólar** (`bd-solo-dolar`): `code = 'USD'` en SQL.

## Escalabilidad

Agregar un mercado nuevo no requiere params nuevos: basta su entrada en
`MarketName` y su set de modos permitidos en `ALLOWED_MODES`
(`api/models/market_request.py`).
