def health_html(app_name: str, version: str):
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{app_name} - Health Check</title>
        <style>
            :root {{
                --primary-main: #02466D;
                --secondary-main: #064469;
                --bg-gradient-start: #0B2B43;
                --bg-gradient-end: #040A10;
                --surface-card: #0A243A;
                --text-primary: #FFFFFF;
                --text-secondary: #8AA0B1;
                --success: #39E079;
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
            h1 {{
                color: var(--text-primary);
                margin: 0 0 1rem 0;
                font-size: 28px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            .status-box {{
                background-color: rgba(57, 224, 121, 0.05); /* Fondo verde translúcido */
                border: 2px solid rgba(57, 224, 121, 0.3);
                border-radius: 12px;
                padding: 2rem 1.5rem;
                margin-bottom: 2rem;
            }}
            .status-text {{
                color: var(--success);
                font-size: 22px;
                font-weight: 800;
                text-transform: uppercase;
                margin: 0 0 0.8rem 0;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }}
            .pulse-dot {{
                width: 12px;
                height: 12px;
                background-color: var(--success);
                border-radius: 50%;
                box-shadow: 0 0 0 0 rgba(57, 224, 121, 0.7);
                animation: pulse 1.5s infinite;
            }}
            @keyframes pulse {{
                0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(57, 224, 121, 0.7); }}
                70% {{ transform: scale(1); box-shadow: 0 0 0 10px rgba(57, 224, 121, 0); }}
                100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(57, 224, 121, 0); }}
            }}
            .info-text {{
                color: var(--text-secondary);
                font-size: 15px;
                margin: 0;
                font-weight: 500;
            }}
            .btn {{
                display: inline-block;
                background-color: transparent;
                border: 2px solid var(--primary-main);
                color: var(--text-primary);
                padding: 12px 32px;
                text-decoration: none;
                border-radius: 12px;
                font-weight: 600;
                transition: background-color 0.2s, transform 0.1s;
                cursor: pointer;
            }}
            .btn:hover {{
                background-color: var(--primary-main);
                transform: translateY(-1px);
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>System Status</h1>
            <div class="status-box">
                <div class="status-text">
                    <div class="pulse-dot"></div>
                    All Systems Operational
                </div>
                <p class="info-text">Service: {app_name} (API v{version})</p>
                <p class="info-text" style="margin-top: 0.5rem; font-size: 13px;">Status Code: 200 OK</p>
            </div>
            <a href="/" class="btn">Volver a Inicio</a>
        </div>
    </body>
    </html>
    """
