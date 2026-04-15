from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

def get_custom_swagger_html(app):
    # Generamos el HTML base de Swagger UI proporcionado por FastAPI
    html_response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_favicon_url="/favicon.ico",
    )
    
    # Extraemos el contenido como string
    html_content = html_response.body.decode("utf-8")
    
    # CSS inyectado para forzar la paleta Dark Mode Premium de DolarTracker
    custom_css = """
    <style>
        /* 1. Fondo general y Base */
        body { margin: 0; background-color: #040A10 !important; color: #FFFFFF !important; }
        .swagger-ui { background-color: #040A10 !important; color: #FFFFFF !important; }

        /* 2. Textos Globales */
        .swagger-ui .info .title, .swagger-ui .info p, .swagger-ui .info li,
        .swagger-ui .info h1, .swagger-ui .info h2, .swagger-ui .info h3, 
        .swagger-ui .info h4, .swagger-ui .info h5, .swagger-ui .info a { color: #FFFFFF !important; }
        .swagger-ui a.nostyle, .swagger-ui .renderedMarkdown p, 
        .swagger-ui .renderedMarkdown a { color: #B0C1CE !important; }

        /* 3. Topbar (Cabecera Superior) */
        .swagger-ui .topbar { background-color: #0A243A !important; border-bottom: 2px solid #02466D !important; padding: 10px 0; }
        .swagger-ui .topbar a { color: #FFFFFF !important; font-weight: bold; }
        
        /* 4. Bloques de Operaciones (Endpoints) */
        .swagger-ui .opblock { border-radius: 8px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important; border: 1px solid #02466D !important; }
        .swagger-ui .opblock .opblock-summary { border-bottom: none !important; }
        
        /* 4.1 Botones REST (GET, POST...) */
        .swagger-ui .opblock .opblock-summary-method { background-color: #39E079 !important; color: #040A10 !important; border-radius: 6px !important; }
        .swagger-ui .opblock.opblock-get { background-color: rgba(10, 36, 58, 0.8) !important; border-color: rgba(57, 224, 121, 0.4) !important; }
        .swagger-ui .opblock.opblock-get .opblock-summary { border-color: rgba(57, 224, 121, 0.4) !important; }
        .swagger-ui .opblock.opblock-post { background-color: rgba(10, 36, 58, 0.8) !important; border-color: rgba(73, 144, 226, 0.4) !important; }
        .swagger-ui .opblock.opblock-post .opblock-summary-method { background-color: #4990E2 !important; color: #FFFFFF !important; }

        /* 5. Secciones desplegables dentro de los Endpoints */
        .swagger-ui .opblock-summary-path, .swagger-ui .opblock-summary-path__deprecated,
        .swagger-ui .opblock-summary-description, .swagger-ui .parameter__name, 
        .swagger-ui .parameter__type, .swagger-ui .parameter__in, 
        .swagger-ui .tab li button.tablinks, .swagger-ui .response-col_status, 
        .swagger-ui .response-col_description, .swagger-ui .response-col_links, 
        .swagger-ui table thead tr th, .swagger-ui .opblock-section-header h4 { color: #FFFFFF !important; }

        /* 6. Fondos de secciones internas (Parámetros / Responses) */
        .swagger-ui .opblock-section-header { background-color: #0A243A !important; border-bottom: 2px solid #02466D !important; }
        .swagger-ui table tbody tr td, .swagger-ui table thead tr th { border-bottom: 1px solid rgba(255,255,255,0.1) !important; }
        
        /* 7. Bloques de Código JSON (Ligeramente más claros) */
        .swagger-ui .opblock-body pre.microlight { background-color: #0B1724 !important; color: #FFFFFF !important; border-radius: 6px !important; }
        .swagger-ui .highlight-code { background-color: #0B1724 !important; }

        /* 8. Botones de interacción generales (Try it out, Execute) */
        .swagger-ui .btn { background-color: transparent !important; color: #39E079 !important; border: 2px solid #39E079 !important; border-radius: 8px !important; transition: all 0.2s; }
        .swagger-ui .btn:hover { background-color: #39E079 !important; color: #040A10 !important; }
        .swagger-ui .btn.execute { background-color: #02466D !important; color: #FFFFFF !important; border-color: #02466D !important; }
        .swagger-ui .btn.execute:hover { background-color: #FFFFFF !important; color: #02466D !important; }
        .swagger-ui .btn.cancel { border-color: #F44336 !important; color: #F44336 !important; }
        .swagger-ui .btn.authorize { color: #FFFFFF !important; border-color: #39E079 !important; }
        .swagger-ui .btn.authorize svg { fill: #39E079 !important; }

        /* 9. Entradas de Texto / Selects */
        .swagger-ui select, .swagger-ui input[type=text] { 
            background-color: #0B1724 !important; color: #FFFFFF !important; border: 1px solid #5E8DAE !important; border-radius: 4px !important; 
        }

        /* 10. Sección de Modelos Inferior */
        .swagger-ui section.models { border-color: #02466D !important; background-color: #0A243A !important; border-radius: 12px !important; }
        .swagger-ui section.models h4 { color: #FFFFFF !important; }
        .swagger-ui section.models .model-container { background-color: #040A10 !important; border-radius: 8px !important; }
        .swagger-ui .model, .swagger-ui .model-title, .swagger-ui .prop-type, .swagger-ui .prop-format { color: #FFFFFF !important; }
        .swagger-ui .model-toggle:after { filter: invert(100%); } /* Invertimos el icono de flechita */
        
        /* 11. Cajas de Autorización Modal */
        .swagger-ui .dialog-ux .modal-ux { background-color: #0A243A !important; border: 1px solid #02466D !important; }
        .swagger-ui .dialog-ux .modal-ux-header { border-bottom: 1px solid #02466D !important; }
        .swagger-ui .dialog-ux .modal-ux-header h3 { color: #FFFFFF !important; }
        .swagger-ui .dialog-ux .modal-ux-content h4 { color: #FFFFFF !important; }
    </style>
    """
    
    # Inyectamos el CSS personalizado justo antes del cierre del <head>
    custom_html = html_content.replace('</head>', f'{custom_css}\n</head>')
    
    return HTMLResponse(content=custom_html)
