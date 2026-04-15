import json
from fastapi.responses import HTMLResponse

def get_custom_redoc_html(app):
    # Definimos el objeto de tema optimizado para legibilidad en modo oscuro
    theme_obj = {
        "colors": {
            "primary": { "main": "#39E079" },  # Acentos y links (usamos el verde éxito para resaltar)
            "success": { "main": "#39E079" },
            "error": { "main": "#F44336" },
            "text": { 
                "primary": "#FFFFFF",          # Texto central principal legible
                "secondary": "#B0C1CE"         # Texto de descripción/metadatos
            },
            "tonal": { "neutral": "#8AA0B1" }
        },
        "sidebar": {
            "backgroundColor": "#0A243A",      # Color oscuro del menú
            "textColor": "#FFFFFF",            # Texto blanco para el menú
            "activeTextColor": "#39E079",      # Resaltador en verde
            "width": "260px"
        },
        "rightPanel": {
            "backgroundColor": "#0B1724",      # Fondo ligeramente más claro para el panel derecho
            "textColor": "#FFFFFF"
        },
        "typography": {
            "fontSize": "16px",
            "fontFamily": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
            "headings": {
                "fontFamily": "system-ui, sans-serif",
                "fontWeight": "700",
                "color": "#FFFFFF"             # Títulos blancos
            },
            "code": {
                "fontSize": "14px",
                "fontFamily": "monospace",
                "backgroundColor": "#0B1621",
                "color": "#FFFFFF"
            }
        }
    }

    # Inicialización imperativa usando Redoc.init (Paso del 'theme' dentro de 'options' corregido)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{app.title} - ReDoc Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="shortcut icon" href="/favicon.ico">
        <style>
            /* Fondo base para evitar parpadeos blancos */
            body {{
                margin: 0;
                padding: 0;
                background-color: #040A10 !important;
                color: #FFFFFF;
            }}
        </style>
    </head>
    <body>
        <div id="redoc-container"></div>
        <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
        <script>
            // Iniciamos Redoc. El segundo parámetro recibe las opciones, donde debe viajar el 'theme'
            Redoc.init(
                "{app.openapi_url}",
                {{ theme: {json.dumps(theme_obj)} }},
                document.getElementById('redoc-container')
            );
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html_content)
