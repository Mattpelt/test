# Guide de déploiement — SkyDive Media Hub

Ce guide couvre l'installation complète sur un PC Ubuntu vierge.
Toutes les commandes SSH sont à exécuter sur le PC cible (`matthieu@192.168.1.39`).

---

## Installation automatique (recommandé)

Un script installe tout en une seule commande :

```bash
sudo apt install -y git && \
git clone https://github.com/Mattpelt/test ~/skydivemediahub && \
bash ~/skydivemediahub/setup.sh
```

Le script effectue automatiquement les étapes 1 à 8 ci-dessous.
Il pose une seule question interactive : le chemin de stockage des vidéos (défaut : `/mnt/hdd_videos`).

À la fin, il affiche les URLs d'accès et les mots de passe générés.

---

## Installation manuelle (étape par étape)

Suivre ce guide si le script échoue ou pour comprendre chaque étape.

---

## Prérequis

- PC sous Ubuntu 22.04 LTS ou 24.04 LTS
- Accès SSH : `ssh matthieu@192.168.1.39`
- Connexion internet sur le PC cible

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
sudo apt install -y ca-certificates curl gnupg lsb-release

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo usermod -aG docker $USER
sudo systemctl enable docker
newgrp docker
```

Vérification :
```bash
docker --version && docker compose version
```

---

## Étape 4 — Cloner le dépôt

```bash
git clone https://github.com/Mattpelt/test ~/skydivemediahub
cd ~/skydivemediahub
```

---

## Étape 5 — Configurer l'environnement (.env)

Créer le fichier `.env` à la racine du projet :

```bash
nano ~/skydivemediahub/.env
```

Contenu minimal :

```env
POSTGRES_USER=skydive
POSTGRES_PASSWORD=<mot_de_passe_fort>
POSTGRES_DB=skydivemediahub
DATABASE_URL=postgresql://skydive:<mot_de_passe_fort>@db:5432/skydivemediahub
VIDEO_STORAGE_PATH=/mnt/hdd_videos
N8N_USER=admin
N8N_PASSWORD=<mot_de_passe_fort>
```

| Variable | Description |
|---|---|
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL — choisir un mot de passe fort |
| `DATABASE_URL` | Même mot de passe que `POSTGRES_PASSWORD` |
| `VIDEO_STORAGE_PATH` | Chemin de montage du HDD de stockage vidéo |
| `N8N_USER` | Login de l'interface n8n (défaut : `admin`) |
| `N8N_PASSWORD` | Mot de passe de l'interface n8n |

> Le `.env` n'est jamais committé dans Git — il contient les secrets.

---

## Étape 6 — Créer le répertoire de stockage vidéo

```bash
sudo mkdir -p /mnt/hdd_videos
sudo chown $USER:$USER /mnt/hdd_videos
```

> Si un HDD SATA dédié est monté ailleurs (ex : `/mnt/sata1`), adapter `VIDEO_STORAGE_PATH` dans le `.env`.

---

## Étape 7 — Démarrer l'application

```bash
docker compose up --build -d
```

Le premier lancement télécharge les images et compile les dépendances (3 à 5 minutes).

Vérification :
```bash
docker compose ps
```

Les trois services doivent être actifs :
```
NAME                         STATUS
skydivemediahub-db-1         running (healthy)
skydivemediahub-backend-1    running
skydivemediahub-n8n-1        running
```

---

## Étape 8 — Vérifier que l'API répond

```bash
curl http://localhost:8000/health
```

Depuis un navigateur sur le réseau local :
```
http://192.168.1.39:8000/docs    → Swagger UI (API backend)
http://192.168.1.39:5678         → Interface n8n (automatisations)
```

---

## Étape 9 — Configurer la détection automatique de caméra (règle udev)

Cette étape permet au PC de détecter une caméra branchée en USB et de lancer l'ingestion automatiquement.

Le script `setup.sh` configure cette étape automatiquement. En cas d'installation manuelle :

### Script MTP/PTP (GoPro, Insta360, Sony…)

```bash
sudo tee /usr/local/bin/skydive-camera.sh > /dev/null <<'EOF'
#!/bin/bash
LOG=/tmp/skydive-camera.log
echo "[$(date)] udev MTP: serial=$ID_SERIAL_SHORT vendor=$ID_VENDOR_ID" >> "$LOG"
/usr/bin/systemd-run --no-block \
  /usr/bin/curl -s -X POST http://127.0.0.1:8000/internal/camera-connected \
  -H "Content-Type: application/json" \
  -d "{\"serial\": \"$ID_SERIAL_SHORT\", \"mtp\": true, \"vendor_id\": \"$ID_VENDOR_ID\"}" >> "$LOG" 2>&1
EOF
sudo chmod +x /usr/local/bin/skydive-camera.sh
```

### Script USB Mass Storage (Insta360 X5, cartes SD…)

```bash
sudo tee /usr/local/bin/skydive-storage.sh > /dev/null <<'EOF'
#!/bin/bash
LOG=/tmp/skydive-camera.log
echo "[$(date)] udev storage: serial=$ID_SERIAL_SHORT device=$DEVNAME" >> "$LOG"
/usr/bin/systemd-run --no-block \
  /usr/bin/curl -s -X POST http://127.0.0.1:8000/internal/camera-connected \
  -H "Content-Type: application/json" \
  -d "{\"serial\": \"$ID_SERIAL_SHORT\", \"mtp\": false, \"device_node\": \"$DEVNAME\"}" >> "$LOG" 2>&1
EOF
sudo chmod +x /usr/local/bin/skydive-storage.sh
```

### Règle udev

```bash
sudo tee /etc/udev/rules.d/99-skydive-camera.rules > /dev/null <<'EOF'
# Caméras MTP/PTP (GoPro, Sony, etc.)
ACTION=="bind", SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ENV{ID_GPHOTO2}=="1", RUN+="/usr/local/bin/skydive-camera.sh"
# Caméras USB Mass Storage (Insta360, cartes SD)
ACTION=="add", SUBSYSTEM=="block", ENV{ID_BUS}=="usb", ENV{DEVTYPE}=="partition", RUN+="/usr/local/bin/skydive-storage.sh"
EOF

sudo udevadm control --reload-rules
```

---

## Étape 10 — Configurer n8n (ingestion automatique des PDFs Afifly)

n8n est l'outil d'automatisation qui surveille la boîte Gmail et envoie les PDFs Afifly reçus au backend.

Le workflow est automatiquement importé au démarrage de n8n, mais les credentials Gmail doivent être configurés manuellement une seule fois.

### 10.1 — Accéder à n8n

Ouvrir dans un navigateur : `http://192.168.1.39:5678`

Se connecter avec les identifiants définis dans le `.env` (`N8N_USER` / `N8N_PASSWORD`).

### 10.2 — Configurer les credentials Gmail (IMAP)

Le workflow *"gmail PDF Afifly poster"* est déjà importé mais inactif.

1. Ouvrir le workflow depuis la liste
2. Cliquer sur le nœud **Email Trigger (IMAP)**
3. Cliquer sur **Credential for IMAP** → **Create new**
4. Remplir les champs :

| Champ | Valeur |
|---|---|
| Host | `imap.gmail.com` |
| Port | `993` |
| SSL | Activé |
| User | `ibelieveicanfly.peltzer@gmail.com` |
| Password | Mot de passe d'application Gmail (voir ci-dessous) |

#### Générer un mot de passe d'application Gmail

1. Aller sur `myaccount.google.com/apppasswords` avec le compte Gmail concerné
   > Prérequis : la validation en 2 étapes doit être activée sur le compte
2. Choisir un nom (ex : `n8n`), cliquer **Créer**
3. Copier le mot de passe à 16 caractères généré
4. Le coller dans le champ **Password** du credential n8n

5. Cliquer **Test** pour vérifier la connexion, puis **Save**

### 10.3 — Activer le workflow

De retour sur la liste des workflows (`http://192.168.1.39:5678/home/workflows`) :

- Le workflow *"gmail PDF Afifly poster"* doit afficher le statut **Published** (point vert)
- S'il est inactif, cliquer sur les 3 points → **Publish**

Le workflow surveille la boîte Gmail en continu et transmet automatiquement chaque PDF Afifly reçu au backend.

### 10.4 — Tester

Envoyer un email avec un PDF Afifly en pièce jointe à l'adresse Gmail configurée.
Dans les logs du backend, vérifier que le rot a bien été créé :

```bash
docker compose logs backend --tail=20
```

Résultat attendu :
```
[ROT] ✚ Créé  — n°XXXX | 2025-12-07 14:30 | 15 participants (2 compte(s) associé(s))
```

Si le rot existait déjà (doublon) :
```
[ROT] ↩ Ignoré — n°XXXX du 2025-12-07 déjà en base et à jour
```

---

## Étape 11 — Mises à jour du code

Pour déployer une nouvelle version depuis GitHub :

```bash
cd ~/skydivemediahub && git pull && docker compose up --build -d
```

> Pour le backend uniquement (sans rebuild Docker) :
> ```bash
> cd ~/skydivemediahub && git pull && docker compose restart backend
> ```

---

## Commandes utiles

```bash
# Logs en temps réel
docker compose logs -f backend
docker compose logs -f n8n

# Redémarrer un service
docker compose restart backend
docker compose restart n8n

# Arrêter tout
docker compose down

# Arrêter et supprimer les données (DANGER : efface la BDD)
docker compose down -v

# Shell dans le container backend
docker compose exec backend bash

# Accès direct à PostgreSQL
docker compose exec db psql -U skydive -d skydivemediahub

# Vérifier les logs udev (détection caméra)
tail -f /tmp/skydive-camera.log
```

---

## Architecture réseau

| Composant | Adresse |
|---|---|
| PC pupitre | `192.168.1.39` |
| API backend | `http://192.168.1.39:8000` |
| Swagger UI | `http://192.168.1.39:8000/docs` |
| n8n | `http://192.168.1.39:5678` |
| PostgreSQL | `localhost:5432` (interne Docker) |
| GoPro (quand branchée) | `172.26.166.51:8080` |

---

## Structure du projet

```
skydivemediahub/
├── backend/
│   ├── app/
│   │   ├── main.py               # Point d'entrée FastAPI + migrations
│   │   ├── database.py           # Connexion PostgreSQL / SQLAlchemy
│   │   ├── models/               # Tables : users, rots, rot_participants, videos, settings
│   │   ├── schemas/              # Schémas Pydantic (validation API)
│   │   ├── routers/              # Endpoints : users, rots, videos, internal, settings
│   │   └── services/             # Logique métier
│   │       ├── pdf_parser.py     # Parsing PDF Afifly (pdfplumber)
│   │       ├── video_ingestor.py # Ingestion caméra (GoPro HTTP / MTP / block)
│   │       ├── matcher.py        # Matching vidéo ↔ rot par horodatage
│   │       ├── rot_service.py    # Création / upsert des rots en base
│   │       └── usb_watcher.py   # Surveillance USB via pyudev
│   ├── Dockerfile
│   └── requirements.txt
├── n8n/
│   └── workflows/
│       └── gmail_pdf_afifly.json # Workflow importé automatiquement au démarrage
├── docker-compose.yml
├── setup.sh                      # Script d'installation automatique
├── .env                          # Configuration locale (jamais committé)
├── README.md                     # Document fonctionnel
└── DEPLOY.md                     # Ce fichier
```

---

## Endpoints API principaux

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/rots` | Upload PDF Afifly → parse + sauvegarde |
| POST | `/rots/json` | Créer un rot depuis JSON (sans PDF) |
| GET | `/rots` | Lister toutes les rotations |
| GET | `/rots/{id}` | Détail d'une rotation |
| POST | `/users` | Créer un compte sautant |
| PATCH | `/users/{id}/cameras` | Associer des numéros de série caméra |
| GET | `/videos/user/{id}` | Vidéos d'un sautant |
| GET | `/settings` | Lire la configuration |
| PATCH | `/settings` | Modifier la configuration |
| POST | `/internal/camera-connected` | Déclencheur d'ingestion (appelé par udev) |
