#!/usr/bin/env python3
"""
Script pour créer le schéma PostgreSQL sur Railway
"""

import psycopg
import sys

# Configuration Railway
DATABASE_URL = "postgresql://postgres:UqtALrZoRLKifgxpMKUhVcfBYGOIdRDK@crossover.proxy.rlwy.net:12593/railway"

def main():
    print("Connexion à PostgreSQL (Railway)...")
    try:
        conn = psycopg.connect(DATABASE_URL)
        print("✓ Connecté à Railway")
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        sys.exit(1)
    
    print("\nCréation du schéma...")
    try:
        with open('schema.sql', 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        cursor = conn.cursor()
        cursor.execute(schema_sql)
        conn.commit()
        print("✓ Schéma créé avec succès")
        
        # Vérifier les tables créées
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"\n✓ Tables créées ({len(tables)}):")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Erreur lors de la création du schéma: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)

if __name__ == '__main__':
    main()
