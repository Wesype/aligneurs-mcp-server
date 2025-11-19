FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt ./

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source et le script de démarrage
COPY mcp_server.py ./
COPY start.sh ./

# Rendre le script exécutable
RUN chmod +x start.sh

# Exposer le port (Railway assignera automatiquement un port)
EXPOSE 8000

# Commande pour démarrer le serveur HTTP
CMD ["./start.sh"]
