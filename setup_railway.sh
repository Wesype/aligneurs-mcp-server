#!/bin/bash

# Script de configuration et d'import pour Railway PostgreSQL

# Configuration Railway
DOMAIN="crossover.proxy.rlwy.net"
PORT="12593"
PASSWORD="UqtALrZoRLKifgxpMKUhVcfBYGOIdRDK"

echo "=== Configuration Railway PostgreSQL ==="
echo "Host: $DOMAIN"
echo "Port: $PORT"
echo ""

# Créer le schéma
echo "=== Création du schéma PostgreSQL ==="
PGPASSWORD=$PASSWORD psql -h "$DOMAIN" -p "$PORT" -U postgres -d railway -f schema.sql

if [ $? -eq 0 ]; then
    echo "✓ Schéma créé avec succès"
else
    echo "✗ Erreur lors de la création du schéma"
    exit 1
fi

echo ""
echo "=== Lancement de l'import ==="
python3 import_csv_to_postgres.py

echo ""
echo "=== Terminé ==="
