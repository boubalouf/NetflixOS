# 🎬 NetflixOS

**NetflixOS** est un orchestrateur multimédia léger conçu pour automatiser la recherche, le téléchargement et la diffusion de contenus (Films & Séries) sur un serveur Debian/Ubuntu.

---

## 💡 Le Concept
L'application sert de pont intelligent entre plusieurs services natifs :
1. Interface (Flask) : Recherche unifiée et gestion.
2. Indexer (Jackett) : Agrégateur de trackers torrents.
3. Downloader (qBittorrent) : Gestion des transferts via Web API.
4. Streamer (Jellyfin/Plex) : Diffusion du contenu indexé.

---

## 🚀 Déploiement Rapide (Native)

### 1. Prérequis
sudo apt update && sudo apt install python3-pip gunicorn jackett qbittorrent-nox jellyfin -y
pip3 install flask requests

### 2. Configuration des Dossiers
mkdir -p ~/downloads/films ~/downloads/series

### 3. Mise en Service (Systemd)
Fichier de service : /etc/systemd/system/netflixos.service

[Unit]
Description=NetflixOS Daemon
After=network.target

[Service]
User="youruser"
WorkingDirectory=/home/"youruser"/NetflixOS
ExecStart=/usr/bin/python3 -m gunicorn --workers 8 --timeout 120 --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target

### 4. Activation
sudo systemctl daemon-reload
sudo systemctl enable --now jackett qbittorrent netflixos jellyfin

---

## ⚙️ Paramètres de Production
* Port par défaut : 5000
* Workers Gunicorn : 8
* Timeout : 120s
* DNS conseillés : 1.1.1.1 / 8.8.8.8

---

## 🛠 Maintenance
* Logs : journalctl -u netflixos -f
* Restart : systemctl restart netflixos
* Statut : systemctl status netflixos
