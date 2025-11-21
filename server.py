#!/usr/bin/env python3
"""
MCP Server pour PostgreSQL - Activités Aligneurs
"""
import os
import asyncio
import psycopg
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL required")

def get_connection():
    return psycopg.connect(DATABASE_URL)

# Créer le serveur MCP
app = Server("aligneurs-db")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="query_sql",
            description="Execute SQL SELECT query on aligneurs database",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL SELECT query"}
                },
                "required": ["sql"]
            }
        ),
        Tool(
            name="get_stats",
            description="Get database statistics",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_schema",
            description="Get database schema",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "query_sql":
        sql = arguments["sql"]
        if not sql.strip().upper().startswith(('SELECT', 'WITH')):
            return [TextContent(type="text", text="Error: Only SELECT queries allowed")]
        
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
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]
    
    elif name == "get_stats":
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
            return [TextContent(type="text", text=f"Total: {row[0]}, Patients: {row[1]}, Period: {row[2]} to {row[3]}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]
    
    elif name == "get_schema":
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
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]
    
    return [TextContent(type="text", text="Unknown tool")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
