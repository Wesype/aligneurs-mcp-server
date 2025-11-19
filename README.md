# Import CSV vers PostgreSQL - Aligneurs Français

Ce projet permet d'importer les données d'activités depuis un fichier CSV vers une base de données PostgreSQL.

## Structure de la base de données

La base de données reconstruit la structure PostgreSQL d'origine avec les tables suivantes :

### Table principale
- **activities** : Table principale contenant toutes les activités avec les informations de base

### Tables de détails (liées par Meta Data)
- **af_setups** : Détails des AF Setups (aligneurs)
- **treatments** : Détails des traitements
- **invoices** : Détails des factures
- **retainers** : Détails des contentions
- **prescriptions** : Détails des prescriptions (avec JSONB pour clinic_objects et clinical_preference)

## Prérequis

1. PostgreSQL installé et en cours d'exécution
2. Python 3.x avec psycopg2

```bash
pip install psycopg2-binary
```

## Configuration

La configuration Railway est déjà pré-configurée dans `import_csv_to_postgres.py` :

```python
DB_CONFIG = {
    'dbname': 'railway',
    'user': 'postgres',
    'password': 'UqtALrZoRLKifgxpMKUhVcfBYGOIdRDK',
    'host': 'crossover.proxy.rlwy.net',
    'port': '12593'
}
```

## Installation

### Option 1: Script automatique (recommandé)

```bash
# Rendre le script exécutable
chmod +x setup_railway.sh

# Lancer le script qui crée le schéma et importe les données
./setup_railway.sh
```

### Option 2: Étapes manuelles

#### 1. Créer le schéma sur Railway

```bash
PGPASSWORD=UqtALrZoRLKifgxpMKUhVcfBYGOIdRDK psql \
  -h crossover.proxy.rlwy.net \
  -p 12593 \
  -U postgres \
  -d railway \
  -f schema.sql
```

#### 2. Importer les données

```bash
python3 import_csv_to_postgres.py
```

## Utilisation

Une fois l'import terminé, vous pouvez interroger les données :

```sql
-- Nombre total d'activités
SELECT COUNT(*) FROM activities;

-- Activités par type
SELECT activity_type, COUNT(*) 
FROM activities 
GROUP BY activity_type 
ORDER BY COUNT(*) DESC;

-- AF Setups avec leurs activités
SELECT a.activity_id, a.description, af.name, af.state, af.price
FROM activities a
JOIN af_setups af ON a.activity_id = af.activity_id
LIMIT 10;

-- Traitements par dentiste
SELECT dentist_first_name, dentist_last_name, COUNT(*) as nb_treatments
FROM activities
WHERE treatment_id IS NOT NULL
GROUP BY dentist_first_name, dentist_last_name
ORDER BY nb_treatments DESC;

-- Factures avec montants
SELECT i.title, i.total_ttc, i.status, a.date_activity
FROM invoices i
JOIN activities a ON i.activity_id = a.activity_id
ORDER BY a.date_activity DESC
LIMIT 10;
```

## Structure du CSV source

Le fichier CSV contient 156,937 lignes avec 22 colonnes principales. La colonne `Meta Data` contient un objet JSON qui est décomposé dans les tables de détails selon le type d'objet (`object_name`).

## Notes

- Le script gère les doublons avec `ON CONFLICT DO NOTHING`
- Les dates françaises sont converties automatiquement
- Les nombres avec virgules sont parsés correctement
- Les champs JSONB dans prescriptions permettent des requêtes avancées
- L'import se fait par batch de 1000 lignes pour optimiser les performances
