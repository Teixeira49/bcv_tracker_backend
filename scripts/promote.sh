#!/usr/bin/env bash
#
# Staged production promote para bcv_tracker (plan Free de Vercel).
#
# Crea un build de PRODUCCIÓN "staged" (no sirve tráfico) y, tras tu OK, lo
# promueve a producción. No requiere merge a main: promueves el build exacto.
#
# Requisitos previos (una sola vez):
#   - vercel CLI linkeado:  vercel login && vercel link
#   - En el dashboard: Settings → Environments → Production → Branch Tracking
#     → "Auto-assign Custom Production Domains" DESACTIVADO.
#
# Uso:  ./scripts/promote.sh
#
set -euo pipefail

if ! command -v vercel >/dev/null 2>&1; then
  echo "✖ El CLI de Vercel no está instalado. Instala:  npm i -g vercel@latest" >&2
  exit 1
fi

echo "▶ Construyendo un deployment de producción STAGED (aún no sirve tráfico)…"
URL="$(vercel --prod --skip-domain --yes)"
echo "✔ Deployment staged: $URL"
echo

read -r -p "¿Promover este build a producción ahora? [y/N] " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
  vercel promote "$URL" --yes
  echo "✔ Promovido a producción."
else
  echo "ℹ Cuando estés listo, corre:  vercel promote $URL"
fi
