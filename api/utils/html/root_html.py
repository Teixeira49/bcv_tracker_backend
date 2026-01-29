def root_html():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>bookstore-inventory-api</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f0f2f5;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .card {
                background-color: #ffffff;
                padding: 2.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 450px;
                width: 90%;
            }
            h1 {
                color: #1a1a1a;
                margin-bottom: 0.5rem;
                font-size: 1.8rem;
            }
            .version {
                color: #666;
                font-size: 0.9rem;
                margin-bottom: 1.5rem;
                background-color: #e4e6eb;
                display: inline-block;
                padding: 0.25rem 0.75rem;
                border-radius: 15px;
                font-weight: 500;
            }
            .message {
                color: #444;
                margin-bottom: 2rem;
                line-height: 1.6;
                font-size: 1.05rem;
            }
            .btn {
                display: inline-block;
                background-color: #007bff;
                color: white;
                padding: 0.8rem 1.5rem;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                transition: background-color 0.2s, transform 0.1s;
            }
            .btn:hover {
                background-color: #0056b3;
                transform: translateY(-1px);
            }
            .btn:active {
                transform: translateY(0);
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Dolar Tracker API</h1>
            <div class="version">v1.0.0</div>
            <p class="message">Un pequeño consejo, escribe /docs en la ruta para ver todas mis funciones</p>
            <a href="/docs" class="btn">Ir a la documentación (Swagger)</a>
        </div>
    </body>
    </html>
    """