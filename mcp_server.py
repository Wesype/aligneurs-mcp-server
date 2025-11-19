#!/usr/bin/env python3
"""
Serveur MCP pour interroger la base PostgreSQL des activités aligneurs
Déployable sur Railway avec transport HTTP/SSE pour Dust
"""

from mcp.server.fastmcp import FastMCP
import psycopg
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la base de données
# Railway injecte automatiquement DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

logger.info(f"DATABASE_URL configured: {DATABASE_URL[:20]}...")

# Configuration du serveur
PORT = int(os.getenv('PORT', 8000))
logger.info(f"Server will listen on port {PORT}")

# Créer le serveur MCP
mcp = FastMCP("Aligneurs Database")

def get_connection():
    """Obtenir une connexion à la base de données"""
    return psycopg.connect(DATABASE_URL)

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

@mcp.tool()
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

if __name__ == "__main__":
    # Lancer le serveur MCP
    logger.info("Starting MCP server...")
    mcp.run(transport="sse", host="0.0.0.0", port=PORT)
