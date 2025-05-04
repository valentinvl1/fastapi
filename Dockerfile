# Utilise une image Python officielle
FROM python:3.11-slim

# Crée un répertoire pour l'app
WORKDIR /app

# Copie les fichiers de l'app
COPY . .

# Installe PDM (ou pip si tu veux)
RUN pip install pdm

# Installe les dépendances du projet avec PDM
RUN pdm install

# Expose le port 8000 pour FastAPI
EXPOSE 8000

# Commande de démarrage (modifie le chemin selon ton app)
CMD ["pdm", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
