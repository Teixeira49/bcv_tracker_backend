def root_html(app_name: str, version: str):
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{app_name} API</title>
        <style>
            :root {{
                --primary-main: #02466D;
                --secondary-main: #064469;
                --bg-gradient-start: #0B2B43;
                --bg-gradient-end: #040A10;
                --surface-card: #0A243A;
                --text-primary: #FFFFFF;
                --text-secondary: #8AA0B1;
                --text-accent: #5E8DAE;
            }}
            body {{
                font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background: linear-gradient(135deg, var(--bg-gradient-start), var(--bg-gradient-end));
                color: var(--text-primary);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }}
            .card {{
                background-color: var(--surface-card);
                padding: 2.5rem;
                border-radius: 16px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
                text-align: center;
                max-width: 480px;
                width: 90%;
            }}
            .logo {{
                width: 120px;
                height: 120px;
                margin-bottom: 1.5rem;
            }}
            h1 {{
                color: var(--text-primary);
                margin: 0 0 0.5rem 0;
                font-size: 32px;
                font-weight: bold;
                letter-spacing: 2px;
                text-transform: uppercase;
            }}
            .version {{
                color: var(--text-primary);
                font-size: 13px;
                margin-bottom: 1.5rem;
                background-color: var(--primary-main);
                display: inline-block;
                padding: 4px 12px;
                border-radius: 16px;
                font-weight: 500;
                letter-spacing: 0.5px;
            }}
            .message {{
                color: var(--text-secondary);
                margin-bottom: 2rem;
                line-height: 1.6;
                font-size: 16px;
                font-weight: 500;
            }}
            .button-group {{
                display: flex;
                flex-direction: column;
                gap: 0.8rem;
            }}
            .btn {{
                display: block;
                background-color: var(--primary-main);
                color: var(--text-primary);
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 12px;
                font-weight: 600;
                transition: background-color 0.2s, transform 0.1s;
            }}
            .btn:hover {{
                background-color: var(--secondary-main);
                transform: translateY(-1px);
            }}
            .btn-secondary {{
                background-color: transparent;
                border: 2px solid var(--primary-main);
            }}
            .btn-accent {{
                background-color: #39E079;
                color: #040A10;
            }}
            .btn-accent:hover {{
                background-color: #2eb361;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <img src="/logo_center.svg" alt="Logo" class="logo">
            <h1>{app_name}</h1>
            <div class="version">v{version}</div>
            <p class="message">Servicio centralizado de monitoreo cambiario para Venezuela. Explora nuestra documentación técnica o descarga la aplicación móvil.</p>
            <div class="button-group">
                <a href="/docs" class="btn">Swagger Documentation</a>
                <a href="/redoc" class="btn btn-secondary">ReDoc UI</a>
                <a href="https://github.com/Teixeira49/bcv_tracker_app" class="btn btn-accent" target="_blank">Descargar App Mobile</a>
            </div>
        </div>
    </body>
    </html>
    """