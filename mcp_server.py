#!/usr/bin/env python3
"""
Serveur MCP pour interroger la base PostgreSQL des activités aligneurs
Déployable sur Railway avec transport HTTP/SSE pour Dust
"""

import os
import json
import asyncio
import logging
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import psycopg

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la base de données
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

logger.info(f"DATABASE_URL configured: {DATABASE_URL[:20]}...")

# Créer l'application FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_connection():
    """Obtenir une connexion à la base de données"""
    return psycopg.connect(DATABASE_URL)

# Health check endpoint
@app.get("/")
async def root():
    """Health check."""
    return {
        "status": "ok",
        "service": "Aligneurs MCP SSE Server",
        "protocol": "mcp/sse",
        "version": "1.0.0"
    }

# SSE endpoint
@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP protocol."""
    
    async def event_stream():
        """Generate SSE events for MCP protocol."""
        try:
            base_url = str(request.base_url).rstrip('/').replace('http://', 'https://')
            endpoint_url = f"{base_url}/message"
            
            yield f"event: endpoint\n"
            yield f"data: {endpoint_url}\n\n"
            
            logger.info(f"SSE connection established, endpoint: {endpoint_url}")
            
            while True:
                if await request.is_disconnected():
                    logger.info("Client disconnected from SSE")
                    break
                await asyncio.sleep(30)
                yield f": heartbeat\n\n"
                
        except Exception as e:
            logger.error(f"SSE error: {e}")
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Message handler
@app.post("/message")
async def handle_message(request: Request):
    """Handle MCP JSON-RPC messages."""
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        msg_id = body.get("id")
        
        logger.info(f"Received MCP message: {method} (id: {msg_id})")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "aligneurs-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": get_tools_list()}
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            result_text = await call_tool(tool_name, arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": result_text
                    }]
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": body.get("id") if 'body' in locals() else None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }

def get_tools_list():
    """Return list of available tools."""
    return [
        {
            "name": "query_sql",
            "description": "Exécute une requête SQL SELECT personnalisée sur la base de données PostgreSQL des activités aligneurs",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "Requête SQL SELECT à exécuter"
                    }
                },
                "required": ["sql"]
            }
        },
        {
            "name": "get_schema_info",
            "description": "Affiche le schéma complet de la base de données avec toutes les tables et colonnes",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "get_activities_stats",
            "description": "Obtient des statistiques générales sur les activités",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "get_activities_by_type",
            "description": "Compte les activités par type",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "get_activities_by_dentist",
            "description": "Liste les activités par dentiste",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Nombre maximum de dentistes à afficher",
                        "default": 20
                    }
                }
            }
        },
        {
            "name": "search_activities",
            "description": "Recherche des activités avec des filtres",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "activity_type": {"type": "string", "description": "Type d'activité"},
                    "patient_id": {"type": "integer", "description": "ID du patient"},
                    "dentist_email": {"type": "string", "description": "Email du dentiste"},
                    "date_from": {"type": "string", "description": "Date de début (YYYY-MM-DD)"},
                    "date_to": {"type": "string", "description": "Date de fin (YYYY-MM-DD)"},
                    "limit": {"type": "integer", "description": "Nombre maximum de résultats", "default": 50}
                }
            }
        },
        {
            "name": "get_patient_activities",
            "description": "Récupère toutes les activités d'un patient",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "integer", "description": "ID du patient"}
                },
                "required": ["patient_id"]
            }
        }
    ]

async def call_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool and return result as JSON string."""
    try:
        if name == "query_sql":
            result = query_sql(arguments["sql"])
        elif name == "get_schema_info":
            result = get_schema_info()
        elif name == "get_activities_stats":
            result = get_activities_stats()
        elif name == "get_activities_by_type":
            result = get_activities_by_type()
        elif name == "get_activities_by_dentist":
            result = get_activities_by_dentist(arguments.get("limit", 20))
        elif name == "search_activities":
            result = search_activities(**arguments)
        elif name == "get_patient_activities":
            result = get_patient_activities(arguments["patient_id"])
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
        
        return result
    
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        return json.dumps({"error": str(e)})

def query_sql(sql: str) -> str:
    """
    Exécute une requête SQL SELECT personnalisée sur la base de données.
    
    L'agent peut construire ses propres requêtes SQL pour interroger les tables:
    - activities: table principale avec toutes les activités
    - af_setups: détails des setups d'aligneurs
    - treatments: détails des traitements
    - invoices: détails des factures
    - retainers: détails des contentions
    - prescriptions: détails des prescriptions
    
    Exemples de requêtes:
    - SELECT COUNT(*) FROM activities WHERE activity_type = 'LAB_SENT_AF_SETUP'
    - SELECT * FROM activities WHERE patient_id = 123 ORDER BY date_activity DESC
    - SELECT dentist_email, COUNT(*) FROM activities GROUP BY dentist_email
    
    Args:
        sql: Requête SQL SELECT à exécuter (seules les SELECT sont autorisées)
        
    Returns:
        Résultats de la requête au format texte tabulaire
    """
    # Sécurité: n'autoriser que les SELECT
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
        return "Erreur: Seules les requêtes SELECT et WITH sont autorisées"
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        
        # Récupérer les résultats
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        # Formater la sortie
        if not rows:
            result = "Aucun résultat"
        else:
            # En-têtes
            result = " | ".join(columns) + "\n"
            result += "-" * (len(result) - 1) + "\n"
            
            # Données (limiter à 100 lignes)
            for row in rows[:100]:
                result += " | ".join(str(val) if val is not None else "NULL" for val in row) + "\n"
            
            if len(rows) > 100:
                result += f"\n... ({len(rows) - 100} lignes supplémentaires non affichées)"
            
            result += f"\nTotal: {len(rows)} lignes"
        
        cursor.close()
        conn.close()
        return result
        
    except Exception as e:
        return f"Erreur SQL: {str(e)}"

def get_activities_stats() -> str:
    """
    Obtient des statistiques sur les activités.
    
    Returns:
        Statistiques générales sur les activités
    """
    sql = """
    SELECT 
        COUNT(*) as total_activities,
        COUNT(DISTINCT activity_type) as nb_types,
        COUNT(DISTINCT patient_id) as nb_patients,
        COUNT(DISTINCT treatment_id) as nb_treatments,
        MIN(date_activity) as premiere_activite,
        MAX(date_activity) as derniere_activite
    FROM activities
    """
    return query_sql(sql)

def get_activities_by_type() -> str:
    """
    Compte les activités par type.
    
    Returns:
        Nombre d'activités par type, triées par ordre décroissant
    """
    sql = """
    SELECT 
        activity_type,
        COUNT(*) as count
    FROM activities
    GROUP BY activity_type
    ORDER BY count DESC
    LIMIT 50
    """
    return query_sql(sql)

def get_activities_by_dentist(limit: int = 20) -> str:
    """
    Liste les activités par dentiste.
    
    Args:
        limit: Nombre maximum de dentistes à afficher (défaut: 20)
        
    Returns:
        Nombre d'activités par dentiste
    """
    sql = f"""
    SELECT 
        dentist_first_name,
        dentist_last_name,
        dentist_email,
        dentist_type,
        COUNT(*) as nb_activities
    FROM activities
    WHERE dentist_first_name IS NOT NULL
    GROUP BY dentist_first_name, dentist_last_name, dentist_email, dentist_type
    ORDER BY nb_activities DESC
    LIMIT {limit}
    """
    return query_sql(sql)

def search_activities(
    activity_type: str = None,
    patient_id: int = None,
    dentist_email: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 50
) -> str:
    """
    Recherche des activités avec des filtres.
    
    Args:
        activity_type: Type d'activité (optionnel)
        patient_id: ID du patient (optionnel)
        dentist_email: Email du dentiste (optionnel)
        date_from: Date de début au format YYYY-MM-DD (optionnel)
        date_to: Date de fin au format YYYY-MM-DD (optionnel)
        limit: Nombre maximum de résultats (défaut: 50)
        
    Returns:
        Liste des activités correspondant aux critères
    """
    conditions = []
    
    if activity_type:
        conditions.append(f"activity_type = '{activity_type}'")
    if patient_id:
        conditions.append(f"patient_id = {patient_id}")
    if dentist_email:
        conditions.append(f"dentist_email = '{dentist_email}'")
    if date_from:
        conditions.append(f"date_activity >= '{date_from}'")
    if date_to:
        conditions.append(f"date_activity <= '{date_to}'")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"""
    SELECT 
        activity_id,
        activity_type,
        description,
        date_activity,
        patient_id,
        dentist_first_name,
        dentist_last_name,
        meta_data_object_name
    FROM activities
    WHERE {where_clause}
    ORDER BY date_activity DESC
    LIMIT {limit}
    """
    return query_sql(sql)

def get_patient_activities(patient_id: int) -> str:
    """
    Récupère toutes les activités d'un patient.
    
    Args:
        patient_id: ID du patient
        
    Returns:
        Liste des activités du patient
    """
    sql = f"""
    SELECT 
        activity_id,
        activity_type,
        description,
        date_activity,
        treatment_id,
        is_finition,
        meta_data_object_name,
        number_of_aligners,
        number_of_refinements,
        number_of_retainers
    FROM activities
    WHERE patient_id = {patient_id}
    ORDER BY date_activity DESC
    """
    return query_sql(sql)

def get_schema_info() -> str:
    """
    Affiche le schéma complet de la base de données avec toutes les tables et colonnes.
    Utile pour que l'agent comprenne la structure avant de construire ses requêtes SQL.
    
    Returns:
        Description détaillée de toutes les tables et leurs colonnes
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Récupérer les tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        result = "=== SCHÉMA DE LA BASE DE DONNÉES ===\n\n"
        
        for table in tables:
            # Récupérer les colonnes de chaque table
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            
            columns = cursor.fetchall()
            
            result += f"Table: {table}\n"
            result += "-" * 80 + "\n"
            
            for col in columns:
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                result += f"  - {col[0]}: {col[1]} {nullable}{default}\n"
            
            result += "\n"
        
        cursor.close()
        conn.close()
        return result
        
    except Exception as e:
        return f"Erreur: {str(e)}"

# Ce bloc n'est plus nécessaire car on utilise start.sh avec uvicorn
# if __name__ == "__main__":
#     import uvicorn
#     PORT = int(os.getenv('PORT', 8000))
#     logger.info(f"Starting Aligneurs MCP server on port {PORT}...")
#     uvicorn.run(app, host="0.0.0.0", port=PORT)
