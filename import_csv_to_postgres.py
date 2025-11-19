#!/usr/bin/env python3
"""
Script d'import du CSV des activités aligneurs vers PostgreSQL
"""

import csv
import json
import psycopg
from datetime import datetime
import sys
import os
from decimal import Decimal

# Configuration de la connexion PostgreSQL (Railway)
# Option 1: Utiliser les variables d'environnement Railway
DATABASE_URL = os.getenv('DATABASE_PUBLIC_URL')

# Option 2: Configuration manuelle avec vos informations Railway
if not DATABASE_URL:
    DB_CONFIG = {
        'dbname': 'railway',
        'user': 'postgres',
        'password': 'UqtALrZoRLKifgxpMKUhVcfBYGOIdRDK',
        'host': 'crossover.proxy.rlwy.net',  # Public Networking
        'port': '12593'                       # Public Port
    }
    # Construire l'URL pour référence
    DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"

def parse_date(date_str):
    """Parse les dates du format français vers timestamp"""
    if not date_str or date_str.strip() == '':
        return None
    
    # Mapping des mois français
    mois_fr = {
        'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
        'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
        'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
    }
    
    try:
        # Format: "juin 20, 2024, 1:29 AM"
        parts = date_str.split(',')
        if len(parts) >= 3:
            date_part = parts[0].strip()  # "juin 20"
            year = parts[1].strip()  # "2024"
            time_part = parts[2].strip()  # "1:29 AM"
            
            # Parse date
            mois_jour = date_part.split()
            mois = mois_fr.get(mois_jour[0].lower())
            jour = mois_jour[1]
            
            # Parse time
            time_parts = time_part.split()
            heure_min = time_parts[0].split(':')
            heure = int(heure_min[0])
            minute = heure_min[1]
            
            # Conversion AM/PM
            if len(time_parts) > 1 and time_parts[1] == 'PM' and heure != 12:
                heure += 12
            elif len(time_parts) > 1 and time_parts[1] == 'AM' and heure == 12:
                heure = 0
            
            return f"{year}-{mois}-{jour.zfill(2)} {str(heure).zfill(2)}:{minute}:00"
    except Exception as e:
        print(f"Erreur parsing date '{date_str}': {e}")
        return None

def parse_number(num_str):
    """Parse les nombres avec virgules (ex: '6,977' -> 6977)"""
    if not num_str or num_str.strip() == '':
        return None
    try:
        return int(num_str.replace(',', '').replace(' ', ''))
    except:
        return None

def parse_decimal(dec_str):
    """Parse les décimaux"""
    if not dec_str or dec_str.strip() == '':
        return None
    try:
        return Decimal(dec_str.replace(',', '.'))
    except:
        return None

def parse_boolean(bool_str):
    """Parse les booléens"""
    if not bool_str or bool_str.strip() == '':
        return None
    return bool_str.lower() == 'true'

def import_activity(cursor, row):
    """Importe une ligne d'activité"""
    try:
        # Parse Meta Data JSON
        meta_data = None
        meta_object_name = None
        num_aligners = None
        num_refinements = None
        num_retainers = None
        
        if row[8]:  # Meta Data column
            try:
                meta_data = json.loads(row[8])
                meta_object_name = meta_data.get('object_name')
                num_aligners = meta_data.get('number_of_aligners')
                num_refinements = meta_data.get('number_of_refinements')
                num_retainers = meta_data.get('number_of_retainers')
            except json.JSONDecodeError as e:
                print(f"Erreur JSON pour activity {row[0]}: {e}")
        
        # Insert dans la table activities
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
            parse_number(row[0]),  # activity_id
            row[1],  # activity_type
            row[2],  # description
            parse_date(row[3]),  # date_activity
            parse_date(row[4]),  # updated_at
            parse_number(row[5]),  # destination_id
            parse_number(row[6]),  # source_id
            parse_boolean(row[7]),  # is_read
            parse_number(row[9]),  # patient_id
            parse_boolean(row[10]),  # is_finition
            parse_number(row[11]),  # treatment_id
            parse_boolean(row[12]),  # email_sent
            row[13],  # dentist_first_name
            row[14],  # dentist_last_name
            row[15],  # dentist_email
            row[16],  # dentist_type
            row[17],  # commercial_en_charge
            row[18],  # commercial_name
            row[19],  # suivi_portefeuille
            row[20],  # id_invoice_pennylane
            parse_decimal(row[21]),  # invoice_amount
            meta_object_name,
            num_aligners,
            num_refinements,
            num_retainers
        ))
        
        # Import des données spécifiques selon le type d'objet
        if meta_data and 'data' in meta_data:
            data = meta_data['data']
            activity_id = parse_number(row[0])
            
            if meta_object_name == 'AFSetup':
                import_af_setup(cursor, activity_id, data)
            elif meta_object_name == 'Treatment':
                import_treatment(cursor, activity_id, data)
            elif meta_object_name == 'Invoice':
                import_invoice(cursor, activity_id, data)
            elif meta_object_name == 'Retainer':
                import_retainer(cursor, activity_id, data)
            elif meta_object_name == 'Prescription':
                import_prescription(cursor, activity_id, data)
        
        return True
    except Exception as e:
        print(f"Erreur import activity {row[0]}: {e}")
        return False

def import_af_setup(cursor, activity_id, data):
    """Importe un AF Setup"""
    try:
        cursor.execute("""
            INSERT INTO af_setups (
                id, activity_id, lab, treatment, name, state, reason, lab_instruct,
                af_view, pdf_file, pdf_image_file, price, discount_amount, paid,
                payment_status, pick_date, shipping_number, shipping_state,
                af_setup_date, updated_at, created_at, is_checked_by_lab,
                is_checked_by_dentist, is_price_changed
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (id) DO NOTHING
        """, (
            data.get('id'),
            activity_id,
            data.get('lab'),
            data.get('treatment'),
            data.get('name'),
            data.get('state'),
            data.get('reason'),
            data.get('lab_instruct'),
            data.get('af_view'),
            data.get('pdf_file'),
            data.get('pdf_image_file'),
            parse_decimal(data.get('price')),
            parse_decimal(data.get('discount_amount')),
            data.get('paid'),
            data.get('payment_status'),
            data.get('pick_date'),
            data.get('shipping_number'),
            data.get('shipping_state'),
            data.get('af_setup_date'),
            data.get('updated_at'),
            data.get('created_at'),
            data.get('is_checked_by_lab'),
            data.get('is_checked_by_dentist'),
            data.get('is_price_changed')
        ))
    except Exception as e:
        print(f"Erreur import AF Setup {data.get('id')}: {e}")

def import_treatment(cursor, activity_id, data):
    """Importe un Treatment"""
    try:
        cursor.execute("""
            INSERT INTO treatments (
                id, activity_id, patient, dentist, state, phase, is_finition,
                parent_treatment_id, finition_index, note_in_production,
                note_in_production_updated_at, updated_at, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (id) DO NOTHING
        """, (
            data.get('id'),
            activity_id,
            data.get('patient'),
            data.get('dentist'),
            data.get('state'),
            data.get('phase'),
            data.get('is_finition'),
            data.get('parent_treatment_id'),
            data.get('finition_index'),
            data.get('note_in_production'),
            data.get('note_in_production_updated_at'),
            data.get('updated_at'),
            data.get('created_at')
        ))
    except Exception as e:
        print(f"Erreur import Treatment {data.get('id')}: {e}")

def import_invoice(cursor, activity_id, data):
    """Importe une Invoice"""
    try:
        cursor.execute("""
            INSERT INTO invoices (
                id, activity_id, type, af_setup, retainer, title, due_date,
                source_name, source_address, destination_name, destination_address,
                description, currency, quantity, unit, unit_price, tax, amount,
                aligner_org_price, aligner_qta, aligner_ttc, aligner_pu_ht,
                aligner_total_ht, aligner_tva, aligner_discount, aligner_discount_rate,
                aligner_discount_type, aligner_promo_code, aligner_prix_ht, aligner_prix_ttc,
                kit_10_qta, kit_10_ttc, kit_10_pu_ht, kit_10_total_ht, kit_10_tva,
                kit_10_prix_ht, kit_10_prix_ttc, kit_16_qta, kit_16_ttc, kit_16_pu_ht,
                kit_16_total_ht, kit_16_tva, kit_16_prix_ht, kit_16_prix_ttc,
                dm_qta, dm_ttc, dm_pu_ht, dm_total_ht, dm_tva, dm_prix_ht, dm_prix_ttc,
                total_ht, total_ttc, total_discount, payment_terms_days,
                due_date_description, status, pdf_file, pdf_image_file,
                stripe_customer_id, updated_at, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (id) DO NOTHING
        """, (
            data.get('id'), activity_id, data.get('type'), data.get('af_setup'),
            data.get('retainer'), data.get('title'), data.get('due_date'),
            data.get('source_name'), data.get('source_address'),
            data.get('destination_name'), data.get('destination_address'),
            data.get('description'), data.get('currency'),
            parse_decimal(data.get('quantity')), data.get('unit'),
            parse_decimal(data.get('unit_price')), parse_decimal(data.get('tax')),
            parse_decimal(data.get('amount')), parse_decimal(data.get('aligner_org_price')),
            parse_decimal(data.get('aligner_qta')), parse_decimal(data.get('aligner_ttc')),
            parse_decimal(data.get('aligner_pu_ht')), parse_decimal(data.get('aligner_total_ht')),
            parse_decimal(data.get('aligner_tva')), parse_decimal(data.get('aligner_discount')),
            parse_decimal(data.get('aligner_discount_rate')), data.get('aligner_discount_type'),
            data.get('aligner_promo_code'), parse_decimal(data.get('aligner_prix_ht')),
            parse_decimal(data.get('aligner_prix_ttc')), parse_decimal(data.get('kit_10_qta')),
            parse_decimal(data.get('kit_10_ttc')), parse_decimal(data.get('kit_10_pu_ht')),
            parse_decimal(data.get('kit_10_total_ht')), parse_decimal(data.get('kit_10_tva')),
            parse_decimal(data.get('kit_10_prix_ht')), parse_decimal(data.get('kit_10_prix_ttc')),
            parse_decimal(data.get('kit_16_qta')), parse_decimal(data.get('kit_16_ttc')),
            parse_decimal(data.get('kit_16_pu_ht')), parse_decimal(data.get('kit_16_total_ht')),
            parse_decimal(data.get('kit_16_tva')), parse_decimal(data.get('kit_16_prix_ht')),
            parse_decimal(data.get('kit_16_prix_ttc')), parse_decimal(data.get('dm_qta')),
            parse_decimal(data.get('dm_ttc')), parse_decimal(data.get('dm_pu_ht')),
            parse_decimal(data.get('dm_total_ht')), parse_decimal(data.get('dm_tva')),
            parse_decimal(data.get('dm_prix_ht')), parse_decimal(data.get('dm_prix_ttc')),
            parse_decimal(data.get('total_ht')), parse_decimal(data.get('total_ttc')),
            parse_decimal(data.get('total_discount')), data.get('payment_terms_days'),
            data.get('due_date_description'), data.get('status'),
            data.get('pdf_file'), data.get('pdf_image_file'),
            data.get('stripe_customer_id'), data.get('updated_at'), data.get('created_at')
        ))
    except Exception as e:
        print(f"Erreur import Invoice {data.get('id')}: {e}")

def import_retainer(cursor, activity_id, data):
    """Importe un Retainer"""
    try:
        cursor.execute("""
            INSERT INTO retainers (
                id, activity_id, patient, treatment, index, state, pick_date,
                impression_type, impression_sub_type, shipping_number, shipping_state,
                dentist_id, dentist_profile_id, arcades_to_deal, number_of_pair,
                kit_balance_10, kit_balance_16, price, order_status,
                is_checked_by_lab, backup_state, updated_at, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (id) DO NOTHING
        """, (
            data.get('id'), activity_id, data.get('patient'), data.get('treatment'),
            data.get('index'), data.get('state'), data.get('pick_date'),
            data.get('impression_type'), data.get('impression_sub_type'),
            data.get('shipping_number'), data.get('shipping_state'),
            data.get('dentist_id'), data.get('dentist_profile_id'),
            data.get('arcades_to_deal'), data.get('number_of_pair'),
            data.get('kit_balance_10'), data.get('kit_balance_16'),
            parse_decimal(data.get('price')), data.get('order_status'),
            data.get('is_checked_by_lab'), data.get('backup_state'),
            data.get('updated_at'), data.get('created_at')
        ))
    except Exception as e:
        print(f"Erreur import Retainer {data.get('id')}: {e}")

def import_prescription(cursor, activity_id, data):
    """Importe une Prescription"""
    try:
        # Parse clinic_objects et clinical_preference en JSONB
        clinic_objects = None
        if data.get('clinic_objects'):
            try:
                clinic_objects = json.dumps(json.loads(data.get('clinic_objects')))
            except:
                clinic_objects = data.get('clinic_objects')
        
        clinical_preference = None
        if data.get('clinical_preference'):
            try:
                clinical_preference = json.dumps(json.loads(data.get('clinical_preference')))
            except:
                clinical_preference = data.get('clinical_preference')
        
        cursor.execute("""
            INSERT INTO prescriptions (
                id, activity_id, treatment, package, package_type, rejection_reason,
                clinic_objects, pdf_file, pdf_image_file, clinical_preference,
                pdf_file_clinic_preference, pdf_image_file_clinic_preference,
                lang_file, phase, sub_phase, updated_at, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (id) DO NOTHING
        """, (
            data.get('id'), activity_id, data.get('treatment'),
            data.get('package'), data.get('package_type'),
            data.get('rejection_reason'), clinic_objects,
            data.get('pdf_file'), data.get('pdf_image_file'),
            clinical_preference, data.get('pdf_file_clinic_preference'),
            data.get('pdf_image_file_clinic_preference'),
            data.get('lang_file'), data.get('phase'), data.get('sub_phase'),
            data.get('updated_at'), data.get('created_at')
        ))
    except Exception as e:
        print(f"Erreur import Prescription {data.get('id')}: {e}")

def main():
    csv_file = '/home/goupilus/Téléchargements/query_result_2025-11-04T10_22_01.982276Z.csv'
    
    print("Connexion à PostgreSQL (Railway)...")
    try:
        if DATABASE_URL:
            # Connexion via URL
            conn = psycopg.connect(DATABASE_URL)
            print(f"✓ Connecté via DATABASE_URL")
        else:
            # Connexion via paramètres
            conn = psycopg.connect(**DB_CONFIG)
            print(f"✓ Connecté à {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        
        cursor = conn.cursor()
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        print("\nVérifiez:")
        print("  - Les variables d'environnement Railway sont définies")
        print("  - Ou modifiez DB_CONFIG avec vos valeurs RAILWAY_TCP_PROXY_DOMAIN et RAILWAY_TCP_PROXY_PORT")
        sys.exit(1)
    
    print("\nImport du CSV...")
    imported = 0
    errors = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            
            for i, row in enumerate(reader, 1):
                if len(row) < 22:
                    print(f"Ligne {i}: nombre de colonnes insuffisant ({len(row)})")
                    errors += 1
                    continue
                
                if import_activity(cursor, row):
                    imported += 1
                else:
                    errors += 1
                
                if i % 1000 == 0:
                    conn.commit()
                    print(f"  {i} lignes traitées ({imported} importées, {errors} erreurs)")
        
        conn.commit()
        print(f"\n✓ Import terminé: {imported} activités importées, {errors} erreurs")
        
    except Exception as e:
        print(f"\n✗ Erreur lors de l'import: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()
