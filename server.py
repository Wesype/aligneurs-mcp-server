#!/usr/bin/env python3
"""
MCP Server pour PostgreSQL - Activités Aligneurs
"""
import os
from urllib.parse import quote_plus
import psycopg
from mcp.server.fastmcp import FastMCP
import uvicorn

# Configuration
DATABASE_URL = os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
PORT = int(os.getenv('PORT', 8000))

# Si DATABASE_URL n'existe pas, construire depuis les composants
if not DATABASE_URL:
    db_host = os.getenv('DATABASE_HOST')
    db_port = os.getenv('DATABASE_PORT', '5432')
    db_name = os.getenv('DATABASE_NAME', 'postgres')
    db_user = os.getenv('DATABASE_USER_NAME')
    db_password = os.getenv('DATABASE_PASSWORD')
    
    if db_host and db_user and db_password:
        # Encoder le mot de passe pour échapper les caractères spéciaux
        encoded_password = quote_plus(db_password)
        DATABASE_URL = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
    else:
        raise ValueError("DATABASE_URL or database credentials required")

def get_connection():
    return psycopg.connect(DATABASE_URL)

# Créer le serveur MCP avec FastMCP
mcp = FastMCP("aligneurs-db")

@mcp.tool()
def query_sql(sql: str) -> str:
    """Execute SQL SELECT query on aligneurs database"""
    if not sql.strip().upper().startswith(('SELECT', 'WITH')):
        return "Error: Only SELECT queries allowed"
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        result = " | ".join(columns) + "\n"
        result += "-" * 80 + "\n"
        for row in rows[:100]:
            result += " | ".join(str(v) if v else "NULL" for v in row) + "\n"
        result += f"\nTotal: {len(rows)} rows"
        
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        import traceback
        return f"Error: {e}\n\nDetails:\n{traceback.format_exc()}"

@mcp.tool()
def get_stats() -> str:
    """Get database statistics from activity_dentist_info table"""
    sql = "SELECT * FROM activity_dentist_info LIMIT 1"
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]
        
        # Formater les résultats de manière lisible
        result = "Statistics from activity_dentist_info:\n\n"
        for col, val in zip(columns, row):
            result += f"{col}: {val}\n"
        
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        import traceback
        return f"Error: {e}\n\nDetails:\n{traceback.format_exc()}"

@mcp.tool()
def get_schema() -> str:
    """Get database schema"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        result = "Tables:\n" + "\n".join(f"- {t}" for t in tables)
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        import traceback
        return f"Error: {e}\n\nDetails:\n{traceback.format_exc()}"

# Créer l'application ASGI avec FastMCP
app = mcp.streamable_http_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
