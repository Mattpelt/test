# Guide de déploiement — SkyDive Media Hub

Ce guide couvre l'installation complète sur un PC Ubuntu vierge (uniquement OpenSSH installé).
Toutes les commandes sont à exécuter en SSH sur le PC cible (`matthieu@192.168.1.39`).

---

## Installation automatique (recommandé)

Un script installe tout en une seule commande. À exécuter en SSH sur le PC cible :

```bash
sudo apt install -y git && \
git clone https://github.com/Mattpelt/test ~/skydivemediahub && \
bash ~/skydivemediahub/setup.sh
```

Le script effectue automatiquement les étapes 1 à 8 décrites ci-dessous.
Il pose une seule question interactive : le chemin de stockage des vidéos (défaut : `/mnt/hdd_videos`).

---

## Installation manuelle (étape par étape)

Suivre ce guide si le script échoue ou pour comprendre chaque étape.

---

## Prérequis

- PC sous Ubuntu (22.04 LTS ou 24.04 LTS recommandé)
- Accès SSH : `ssh matthieu@192.168.1.39`
- Connexion internet sur le PC cible
- Le repo GitHub : `https://github.com/Mattpelt/test`

---

## Étape 1 — Mise à jour du système

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Étape 2 — Installer Git

```bash
sudo apt install -y git
```

---

## Étape 3 — Installer Docker

```bash
# Dépendances
sudo apt install -y ca-certificates curl gnupg lsb-release

# Clé GPG officielle Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Dépôt Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installation
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Permettre d'utiliser Docker sans sudo
sudo usermod -aG docker $USER
newgrp docker
```

Vérification :
```bash
docker --version
docker compose version
```

Activer Docker au démarrage du PC :
```bash
sudo systemctl enable docker
```

---

## Étape 4 — Cloner le dépôt

```bash
cd ~
git clone https://github.com/Mattpelt/test skydivemediahub
cd skydivemediahub
```

---

## Étape 5 — Configurer l'environnement

```bash
cp .env.example .env
nano .env
```

Adapter les valeurs suivantes :

| Variable | Valeur par défaut | À modifier |
|---|---|---|
| `POSTGRES_PASSWORD` | `changeme` | **Oui** — choisir un mot de passe fort |
| `DATABASE_URL` | `postgresql://skydive:changeme@db:5432/...` | **Oui** — même mot de passe que ci-dessus |
| `VIDEO_STORAGE_PATH` | `/mnt/hdd_videos` | Si les vidéos sont stockées ailleurs |

Exemple de `.env` complet :
```env
POSTGRES_USER=skydive
POSTGRES_PASSWORD=motdepassefort
POSTGRES_DB=skydivemediahub
DATABASE_URL=postgresql://skydive:motdepassefort@db:5432/skydivemediahub
VIDEO_STORAGE_PATH=/mnt/hdd_videos
```

---

## Étape 6 — Créer le répertoire de stockage vidéo

```bash
sudo mkdir -p /mnt/hdd_videos
sudo chown $USER:$USER /mnt/hdd_videos
```

> Si un HDD SATA dédié est monté à un autre chemin (ex : `/mnt/sata1`),
> adapter `VIDEO_STORAGE_PATH` dans le `.env` en conséquence.

---

## Étape 7 — Démarrer l'application

```bash
docker compose up --build -d
```

Le premier lancement télécharge les images Docker et compile les dépendances — prévoir 3 à 5 minutes.

Vérification :
```bash
docker compose ps
```

Tous les services doivent afficher `running` :
```
NAME                    STATUS
skydivemediahub-db-1        running (healthy)
skydivemediahub-backend-1   running
```

---

## Étape 8 — Vérifier que l'API répond

Depuis le PC Ubuntu :
```bash
curl http://localhost:8000/docs
```

Depuis un navigateur sur le réseau local :
```
http://192.168.1.39:8000/docs
```

La page Swagger UI doit s'afficher avec tous les endpoints.

---

## Étape 9 — Configurer la détection automatique de caméra (règle udev)

Cette étape permet au PC de détecter automatiquement une caméra branchée en USB
et de déclencher l'ingestion des vidéos.

### Créer le script de déclenchement

```bash
sudo nano /usr/local/bin/skydive-camera.sh
```

Contenu :
```bash
#!/bin/bash
curl -s -X POST http://localhost:8000/internal/camera-connected \
  -H "Content-Type: application/json" \
  -d "{\"serial\": \"$ID_SERIAL_SHORT\", \"mtp\": true, \"vendor_id\": \"$ID_VENDOR_ID\"}"
```

Rendre le script exécutable :
```bash
sudo chmod +x /usr/local/bin/skydive-camera.sh
```

### Créer la règle udev

```bash
sudo nano /etc/udev/rules.d/99-skydive-camera.rules
```

Contenu :
```
ACTION=="bind", SUBSYSTEM=="usb", DEVTYPE=="usb_device", ENV{ID_GPHOTO2}=="1", \
RUN+="/usr/local/bin/skydive-camera.sh"
```

Recharger les règles udev :
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

---

## Étape 10 — Mises à jour du code

Pour déployer une nouvelle version depuis GitHub :

```bash
cd ~/skydivemediahub
git pull
docker compose up --build -d
```

---

## Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f backend

# Redémarrer uniquement le backend
docker compose restart backend

# Arrêter tout
docker compose down

# Arrêter et supprimer les données (DANGER : efface la BDD)
docker compose down -v

# Accéder au shell du container backend
docker compose exec backend bash

# Accéder à la base de données PostgreSQL
docker compose exec db psql -U skydive -d skydivemediahub
```

---

## Architecture réseau locale

| Composant | Adresse |
|---|---|
| PC pupitre | `192.168.1.39` |
| API backend | `http://192.168.1.39:8000` |
| Swagger UI | `http://192.168.1.39:8000/docs` |
| PostgreSQL | `localhost:5432` (interne Docker uniquement) |
| GoPro (quand branchée) | `172.26.166.51:8080` |

---

## Structure du projet

```
skydivemediahub/
├── backend/
│   ├── app/
│   │   ├── main.py               # Point d'entrée FastAPI
│   │   ├── database.py           # Connexion PostgreSQL / SQLAlchemy
│   │   ├── models/               # Tables : users, rots, videos, settings
│   │   ├── schemas/              # Schémas Pydantic (validation API)
│   │   ├── routers/              # Endpoints : users, rots, videos, internal
│   │   └── services/             # Logique métier : pdf_parser, video_ingestor
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example                  # Modèle de configuration (copier en .env)
├── .env                          # Configuration locale (jamais committé)
├── README.md                     # Document fonctionnel
└── DEPLOY.md                     # Ce fichier
```
