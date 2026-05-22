#!/bin/bash
# ── VerifAI Docker Fix Script ─────────────────────────────────────────────────
# Run this if you see "ContainerConfig" or other Docker errors
echo "Stopping and removing all old VerifAI containers..."
docker stop verifai-backend verifai-frontend verifai-db 2>/dev/null || true
docker rm -f verifai-backend verifai-frontend verifai-db 2>/dev/null || true

echo "Removing old images..."
docker rmi -f verifai-project_backend verifai-project_frontend 2>/dev/null || true

echo "Pruning unused networks..."
docker network prune -f

echo "Done! Now run:  docker-compose up --build"
