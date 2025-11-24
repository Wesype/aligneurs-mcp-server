#!/usr/bin/env python3
"""
MCP Server pour PostgreSQL - Activités Aligneurs
"""
import os
import psycopg
from mcp.server.fastmcp import FastMCP
import uvicorn

# Configuration
DATABASE_URL = os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
PORT = int(os.getenv('PORT', 8000))

if not DATABASE_URL:
    raise ValueError("DATABASE_URL or DATABASE_PUBLIC_URL required")

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
    """Get database statistics"""
    sql = """
    SELECT 
        COUNT(*) as total,
        COUNT(DISTINCT patient_id) as patients,
        MIN(date_activity) as first_date,
        MAX(date_activity) as last_date
    FROM activities
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"Total: {row[0]}, Patients: {row[1]}, Period: {row[2]} to {row[3]}"
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
