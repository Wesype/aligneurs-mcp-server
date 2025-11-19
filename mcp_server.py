#!/usr/bin/env python3
"""
Serveur MCP pour interroger la base PostgreSQL des activités aligneurs
"""

import os
import psycopg
from fastmcp import FastMCP

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Créer le serveur MCP
mcp = FastMCP("Aligneurs Database")

def get_connection():
    """Obtenir une connexion à la base de données"""
    return psycopg.connect(DATABASE_URL)

@mcp.tool()
def query_sql(sql: str) -> str:
    """Exécute une requête SQL SELECT sur la base de données."""
    if not sql.strip().upper().startswith(('SELECT', 'WITH')):
        return "Erreur: Seules les requêtes SELECT et WITH sont autorisées"
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        if not rows:
            result = "Aucun résultat"
        else:
            result = " | ".join(columns) + "\n"
            result += "-" * (len(result) - 1) + "\n"
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

@mcp.tool()
def get_activities_stats() -> str:
    """Obtient des statistiques sur les activités."""
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

@mcp.tool()
def get_activities_by_type() -> str:
    """Compte les activités par type."""
    sql = """
    SELECT activity_type, COUNT(*) as count
    FROM activities
    GROUP BY activity_type
    ORDER BY count DESC
    LIMIT 50
    """
    return query_sql(sql)

@mcp.tool()
def get_patient_activities(patient_id: int) -> str:
    """Récupère toutes les activités d'un patient."""
    sql = f"""
    SELECT 
        activity_id, activity_type, description, date_activity,
        treatment_id, is_finition, meta_data_object_name,
        number_of_aligners, number_of_refinements, number_of_retainers
    FROM activities
    WHERE patient_id = {patient_id}
    ORDER BY date_activity DESC
    """
    return query_sql(sql)

@mcp.tool()
def get_schema_info() -> str:
    """Affiche le schéma de la base de données."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        result = "=== SCHÉMA DE LA BASE ===\n\n"
        for table in tables:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            columns = cursor.fetchall()
            result += f"Table: {table}\n" + "-" * 80 + "\n"
            for col in columns:
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                result += f"  - {col[0]}: {col[1]} {nullable}\n"
            result += "\n"
        
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        return f"Erreur: {str(e)}"
