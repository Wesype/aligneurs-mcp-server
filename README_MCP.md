# Serveur MCP pour la base de données Aligneurs

Ce serveur MCP permet d'interroger la base PostgreSQL des activités aligneurs via le Model Context Protocol.

## Installation

```bash
# Installer les dépendances
pip install mcp psycopg[binary]
```

## Configuration

Le serveur se connecte par défaut à Railway. Pour utiliser une autre base (AWS, etc.), modifiez la variable `DATABASE_URL` dans `mcp_server.py` ou définissez-la en variable d'environnement :

```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

## Lancement du serveur

```bash
python mcp_server.py
```

## Outils disponibles

### 1. `query_sql` - Requêtes SQL personnalisées ⭐

L'agent peut construire et exécuter ses propres requêtes SQL SELECT.

**Exemples :**
```sql
SELECT COUNT(*) FROM activities WHERE activity_type = 'LAB_SENT_AF_SETUP'
SELECT * FROM activities WHERE patient_id = 123 ORDER BY date_activity DESC
SELECT dentist_email, COUNT(*) as total FROM activities GROUP BY dentist_email
```

### 2. `get_schema_info` - Schéma de la base

Affiche toutes les tables et colonnes pour que l'agent comprenne la structure.

### 3. `get_activities_stats` - Statistiques générales

Statistiques globales : nombre total d'activités, patients, traitements, etc.

### 4. `get_activities_by_type` - Activités par type

Compte les activités groupées par type.

### 5. `get_activities_by_dentist` - Activités par dentiste

Liste les dentistes avec leur nombre d'activités.

### 6. `search_activities` - Recherche avec filtres

Recherche d'activités avec filtres multiples :
- `activity_type` : type d'activité
- `patient_id` : ID du patient
- `dentist_email` : email du dentiste
- `date_from` / `date_to` : période
- `limit` : nombre de résultats

### 7. `get_patient_activities` - Activités d'un patient

Toutes les activités d'un patient spécifique.

## Structure de la base

### Table `activities` (principale)
- `activity_id` : ID unique
- `activity_type` : Type d'activité
- `description` : Description
- `date_activity` : Date de l'activité
- `patient_id` : ID du patient
- `treatment_id` : ID du traitement
- `dentist_first_name`, `dentist_last_name`, `dentist_email` : Info dentiste
- `meta_data_object_name` : Type d'objet (AFSetup, Treatment, Invoice, etc.)
- `number_of_aligners`, `number_of_refinements`, `number_of_retainers` : Compteurs

### Tables de détails
- `af_setups` : Détails des setups d'aligneurs
- `treatments` : Détails des traitements
- `invoices` : Détails des factures
- `retainers` : Détails des contentions
- `prescriptions` : Détails des prescriptions

## Utilisation avec Windsurf

Ajoutez le serveur MCP dans votre configuration Windsurf pour que l'agent puisse interroger directement la base de données.

L'agent pourra :
- ✅ Construire ses propres requêtes SQL
- ✅ Analyser les données
- ✅ Générer des statistiques
- ✅ Rechercher des informations spécifiques
- ✅ Croiser les données entre tables
