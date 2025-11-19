#!/usr/bin/env python3
"""
Script d'import optimisé du CSV des activités aligneurs vers PostgreSQL
Version avec batch inserts et meilleure gestion de la progression
"""

import csv
import json
import psycopg
from datetime import datetime
import sys
import os
from decimal import Decimal
import time

# Augmenter la limite de taille des champs CSV (pour les gros JSON)
csv.field_size_limit(10 * 1024 * 1024)  # 10 MB

# Configuration Railway
DATABASE_URL = "postgresql://postgres:UqtALrZoRLKifgxpMKUhVcfBYGOIdRDK@crossover.proxy.rlwy.net:12593/railway"

def parse_date(date_str):
    """Parse les dates du format français vers timestamp"""
    if not date_str or date_str.strip() == '':
        return None
    
    mois_fr = {
        'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
        'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
        'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
    }
    
    try:
        parts = date_str.split(',')
        if len(parts) >= 3:
            date_part = parts[0].strip()
            year = parts[1].strip()
            time_part = parts[2].strip()
            
            mois_jour = date_part.split()
            mois = mois_fr.get(mois_jour[0].lower())
            jour = mois_jour[1]
            
            time_parts = time_part.split()
            heure_min = time_parts[0].split(':')
            heure = int(heure_min[0])
            minute = heure_min[1]
            
            if len(time_parts) > 1 and time_parts[1] == 'PM' and heure != 12:
                heure += 12
            elif len(time_parts) > 1 and time_parts[1] == 'AM' and heure == 12:
                heure = 0
            
            return f"{year}-{mois}-{jour.zfill(2)} {str(heure).zfill(2)}:{minute}:00"
    except:
        return None

def parse_number(num_str):
    if not num_str or num_str.strip() == '':
        return None
    try:
        return int(num_str.replace(',', '').replace(' ', ''))
    except:
        return None

def parse_decimal(dec_str):
    if not dec_str or dec_str.strip() == '':
        return None
    try:
        return Decimal(dec_str.replace(',', '.'))
    except:
        return None

def parse_boolean(bool_str):
    if not bool_str or bool_str.strip() == '':
        return None
    return bool_str.lower() == 'true'

def main():
    csv_file = '/home/goupilus/Téléchargements/query_result_2025-11-04T10_22_01.982276Z.csv'
    
    print("Connexion à PostgreSQL (Railway)...")
    start_time = time.time()
    
    try:
        conn = psycopg.connect(DATABASE_URL)
        print(f"✓ Connecté à Railway")
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        sys.exit(1)
    
    cursor = conn.cursor()
    
    print("\nComptage des lignes du CSV...")
    with open(csv_file, 'r', encoding='utf-8') as f:
        total_lines = sum(1 for _ in f) - 1  # -1 pour le header
    print(f"Total: {total_lines:,} lignes à importer")
    
    print("\nImport du CSV...")
    imported = 0
    errors = 0
    skipped = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            
            for i, row in enumerate(reader, 1):
                if len(row) < 22:
                    errors += 1
                    continue
                
                try:
                    # Parse Meta Data
                    meta_data = None
                    meta_object_name = None
                    num_aligners = None
                    num_refinements = None
                    num_retainers = None
                    
                    if row[8]:
                        try:
                            meta_data = json.loads(row[8])
                            meta_object_name = meta_data.get('object_name')
                            num_aligners = meta_data.get('number_of_aligners')
                            num_refinements = meta_data.get('number_of_refinements')
                            num_retainers = meta_data.get('number_of_retainers')
                        except:
                            pass
                    
                    # Insert activity
                    cursor.execute("""
                        INSERT INTO activities (
                            activity_id, activity_type, description, date_activity, updated_at,
                            destination_id, source_id, is_read, patient_id, is_finition,
                            treatment_id, email_sent, dentist_first_name, dentist_last_name,
                            dentist_email, dentist_type, commercial_en_charge, commercial_name,
                            suivi_portefeuille, id_invoice_pennylane, invoice_amount,
                            meta_data_object_name, number_of_aligners, number_of_refinements,
                            number_of_retainers
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (activity_id) DO NOTHING
                    """, (
                        parse_number(row[0]), row[1], row[2], parse_date(row[3]), parse_date(row[4]),
                        parse_number(row[5]), parse_number(row[6]), parse_boolean(row[7]),
                        parse_number(row[9]), parse_boolean(row[10]), parse_number(row[11]),
                        parse_boolean(row[12]), row[13], row[14], row[15], row[16], row[17],
                        row[18], row[19], row[20], parse_decimal(row[21]),
                        meta_object_name, num_aligners, num_refinements, num_retainers
                    ))
                    
                    imported += 1
                    
                    # Commit tous les 100 lignes
                    if i % 100 == 0:
                        conn.commit()
                    
                    # Afficher progression tous les 1000
                    if i % 1000 == 0:
                        elapsed = time.time() - start_time
                        rate = i / elapsed
                        remaining = (total_lines - i) / rate if rate > 0 else 0
                        progress = (i / total_lines) * 100
                        print(f"  {i:,}/{total_lines:,} ({progress:.1f}%) - {imported:,} importées, {errors} erreurs - {rate:.0f} lignes/s - ETA: {remaining/60:.1f}min")
                
                except Exception as e:
                    errors += 1
                    if errors < 10:  # Afficher seulement les 10 premières erreurs
                        print(f"Erreur ligne {i}: {e}")
        
        conn.commit()
        elapsed = time.time() - start_time
        print(f"\n✓ Import terminé en {elapsed/60:.1f} minutes")
        print(f"  - {imported:,} activités importées")
        print(f"  - {errors} erreurs")
        
        # Statistiques
        cursor.execute("SELECT COUNT(*) FROM activities")
        total = cursor.fetchone()[0]
        print(f"\n✓ Total dans la base: {total:,} activités")
        
    except Exception as e:
        print(f"\n✗ Erreur: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()
