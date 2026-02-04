#!/bin/bash
clear
echo "🎬 --- INSTALLATION AUTOMATISÉE NETFLIXOS --- 🎬"
IP_LOCALE=$(hostname -I | awk '{print $1}')

# 1. Création des dossiers
mkdir -p config/qbit config/jellyfin config/jackett media/films media/series
chmod -R 777 media/

# 2. Collecte des clés
read -p "🔑 Clé TMDB : " TMDB
read -p "🔑 Clé OMDB : " OMDB
read -p "🔐 Mot de passe qBittorrent : " PASS

echo "🚀 Lancement de Docker..."
docker-compose up -d --build

echo ""
echo "----------------------------------------------------"
echo "🛠️  ÉTAPE 1 : CONFIGURATION JACKETT"
echo "----------------------------------------------------"
echo "1. Va sur http://$IP_LOCALE:9117"
echo "2. Ajoute tes serveurs (+ Add Indexer)"
echo "3. Copie la 'API Key' en haut à droite."
read -p "🔑 Colle la API Key de Jackett : " JACKETT

echo ""
echo "----------------------------------------------------"
echo "🛠️  ÉTAPE 2 : CONFIGURATION JELLYFIN & API"
echo "----------------------------------------------------"
echo "1. Va sur http://$IP_LOCALE:8096"
echo "2. Crée ton compte et ajoute les dossiers /media/films et /media/series"
echo "3. Va dans Tableau de Bord > Clés API (en bas à gauche)"
echo "4. Crée une clé nommée 'NetflixOS' et copie-la."
read -p "🔑 Colle la clé API de Jellyfin : " JELLY_API

# Mise à jour du .env
cat <<EOF > .env
TMDB_KEY=$TMDB
OMDB_KEY=$OMDB
JACKETT_KEY=$JACKETT
QB_PASS=$PASS
JELLY_KEY=$JELLY_API
EOF

docker-compose restart netflixos

echo ""
echo "----------------------------------------------------"
echo "🛠️  ÉTAPE 3 : LE LIEN QBITTORRENT -> JELLYFIN"
echo "----------------------------------------------------"
echo "1. Va sur http://$IP_LOCALE:8080 (Login: admin / MDP dans logs)"
echo "2. Options > Web UI : Change le MDP pour '$PASS'"
echo "3. Options > Téléchargements > 'Exécuter un programme externe' :"
echo "4. COCHE LA CASE et colle cette ligne EXACTEMENT :"
echo "curl -d \"\" \"http://jellyfin:8096/Library/Refresh?api_key=$JELLY_API\""
echo "----------------------------------------------------"
echo "✅ TOUT EST LIÉ ! Ton film apparaîtra sur Jellyfin dès la fin du download."
