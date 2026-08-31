import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api import incidents, ingestion
from app.config.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Incident Management Platform",
    description="AI-powered Incident Management with historical retrieval and resolution recommendations",
    version="1.0.0",
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if they exist
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Custom Swagger UI route - tries local files first, falls back to CDN
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    swagger_ui_dir = Path(__file__).parent / "static" / "swagger-ui"
    
    # Check if local Swagger UI files exist
    if (swagger_ui_dir / "swagger-ui-bundle.js").exists():
        logger.info("Using local Swagger UI files")
        html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{app.title} - Swagger UI</title>
                <link rel="stylesheet" type="text/css" href="/static/swagger-ui/swagger-ui.css">
                <style>
                    html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
                    *, *:before, *:after {{ box-sizing: inherit; }}
                    body {{ margin: 0; padding: 0; }}
                </style>
            </head>
            <body>
                <div id="swagger-ui"></div>
                <script src="/static/swagger-ui/swagger-ui-bundle.js"></script>
                <script src="/static/swagger-ui/swagger-ui-standalone-preset.js"></script>
                <script>
                    window.onload = function() {{
                        const ui = SwaggerUIBundle({{
                            url: "/openapi.json",
                            dom_id: '#swagger-ui',
                            deepLinking: true,
                            presets: [
                                SwaggerUIBundle.presets.apis,
                                SwaggerUIStandalonePreset
                            ],
                            plugins: [
                                SwaggerUIBundle.plugins.DownloadUrl
                            ],
                            layout: "StandaloneLayout"
                        }});
                        window.ui = ui;
                    }}
                </script>
            </body>
            </html>
        """
        return HTMLResponse(content=html_content)
    
    # Fallback to CDN with multiple sources
    logger.info("Using CDN-based Swagger UI (local files not found)")
    html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Incident Management Platform - API Documentation</title>
            <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
            <style>
                html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
                *, *:before, *:after { box-sizing: inherit; }
                body { margin: 0; padding: 0; }
                .cdn-error {
                    padding: 40px;
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                }
                .cdn-error h1 { color: #e74c3c; }
                .cdn-error a { color: #3498db; text-decoration: none; }
                .cdn-error a:hover { text-decoration: underline; }
                .endpoint-list { background: #f5f5f5; padding: 20px; border-radius: 5px; }
                .endpoint-list li { margin: 10px 0; font-family: monospace; }
            </style>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
            <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
            <script>
                setTimeout(function() {
                    if (typeof SwaggerUIBundle === 'undefined') {
                        document.getElementById('swagger-ui').innerHTML = `
                            <div class="cdn-error">
                                <h1>⚠️ Unable to Load Swagger UI</h1>
                                <p>The Swagger UI JavaScript files could not be loaded from the CDN. This may be due to:</p>
                                <ul>
                                    <li>Firewall blocking CDN access</li>
                                    <li>Network restrictions</li>
                                    <li>Corporate proxy settings</li>
                                </ul>
                                
                                <h2>📋 Alternative: View OpenAPI Specification</h2>
                                <p>Click here to view the raw API specification: <a href="/openapi.json" target="_blank"><strong>OpenAPI JSON</strong></a></p>
                                
                                <h2>🔧 Solution: Install Local Swagger UI</h2>
                                <p>Run this command in your backend directory:</p>
                                <pre style="background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto;">python setup_swagger.py</pre>
                                <p>Then restart the server and reload this page.</p>
                                
                                <h2>📌 Available API Endpoints</h2>
                                <div class="endpoint-list">
                                    <h3>Health & Dashboard</h3>
                                    <ul>
                                        <li>GET /api/health - Health check</li>
                                        <li>GET /api/dashboard - Dashboard statistics</li>
                                    </ul>
                                    
                                    <h3>Incidents</h3>
                                    <ul>
                                        <li>GET /api/incidents - List all incidents</li>
                                        <li>GET /api/incidents/search?q=query - Search incidents</li>
                                        <li>GET /api/incidents/{incident_id} - Get specific incident</li>
                                        <li>GET /api/incidents/{incident_id}/conversation - Get incident conversation</li>
                                        <li>POST /api/incidents/analyze - Analyze new incident</li>
                                        <li>POST /api/incidents/chat - Chat about incidents</li>
                                    </ul>
                                    
                                    <h3>Data Ingestion</h3>
                                    <ul>
                                        <li>POST /api/ingestion/mock-chat - Ingest mock chat data</li>
                                    </ul>
                                </div>
                                
                                <h2>🔗 Use with API Clients</h2>
                                <p>Import the OpenAPI spec into:</p>
                                <ul>
                                    <li><strong>Postman:</strong> Import → Link → http://127.0.0.1:8000/openapi.json</li>
                                    <li><strong>Insomnia:</strong> Create → Import From → URL</li>
                                    <li><strong>Bruno:</strong> Collection → Import → OpenAPI</li>
                                </ul>
                            </div>
                        `;
                    } else {
                        const ui = SwaggerUIBundle({
                            url: "/openapi.json",
                            dom_id: '#swagger-ui',
                            deepLinking: true,
                            presets: [
                                SwaggerUIBundle.presets.apis,
                                SwaggerUIStandalonePreset
                            ],
                            plugins: [
                                SwaggerUIBundle.plugins.DownloadUrl
                            ],
                            layout: "StandaloneLayout"
                        });
                        window.ui = ui;
                    }
                }, 1000);
            </script>
        </body>
        </html>
    """
    return HTMLResponse(content=html_content)


# Alternative: ReDoc documentation  
@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>API Documentation - ReDoc</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <style>
                body { margin: 0; padding: 0; }
            </style>
        </head>
        <body>
            <redoc spec-url='/openapi.json'></redoc>
            <script src="https://unpkg.com/redoc@next/bundles/redoc.standalone.js"></script>
        </body>
        </html>
    """)


app.include_router(incidents.router)
app.include_router(ingestion.router)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/dashboard")
def dashboard():
    from app.repositories.incident_repository import get_incident_repository
    repo = get_incident_repository()
    all_incidents = repo.get_all()
    
    applications = set()
    root_causes = {}
    high_severity = 0
    resolved = 0

    for inc in all_incidents:
        applications.add(inc.application)
        if inc.severity in ("HIGH", "CRITICAL"):
            high_severity += 1
        if inc.status == "RESOLVED":
            resolved += 1
        if inc.root_cause:
            rc = inc.root_cause[:50]
            root_causes[rc] = root_causes.get(rc, 0) + 1

    top_root_causes = sorted(root_causes.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_incidents": len(all_incidents),
        "resolved_incidents": resolved,
        "applications_affected": list(applications),
        "high_severity_count": high_severity,
        "top_root_causes": [{"cause": c, "count": n} for c, n in top_root_causes],
    }
