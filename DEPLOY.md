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
SECRET_KEY=<64_hex_chars>
N8N_USER=admin
N8N_PASSWORD=<mot_de_passe_fort>
```

| Variable | Description |
|---|---|
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL — choisir un mot de passe fort |
| `DATABASE_URL` | Même mot de passe que `POSTGRES_PASSWORD` |
| `VIDEO_STORAGE_PATH` | Chemin de montage du HDD de stockage vidéo |
| `SECRET_KEY` | Clé de signature JWT (64 hex chars — généré par setup.sh) |
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

Les quatre services doivent être actifs :
```
NAME                           STATUS
skydivemediahub-db-1           running (healthy)
skydivemediahub-backend-1      running
skydivemediahub-frontend-1     running
skydivemediahub-n8n-1          running
```

---

## Étape 8 — Vérifier que l'application répond

```bash
curl http://localhost:8000/health
```

Depuis un navigateur sur le réseau local :
```
http://192.168.1.39              → Interface web (login / sautants / admin)
http://192.168.1.39:8000/docs    → Swagger UI (API backend)
http://192.168.1.39:5678         → Interface n8n (automatisations)
```

---

## Étape 9 — Créer le premier compte administrateur

Une fois l'application démarrée, créez le compte admin initial :

```bash
docker compose exec backend python -c "
from app.database import SessionLocal
from app.models.user import User
from passlib.context import CryptContext

db = SessionLocal()
pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')
user = User(
    first_name='Admin',
    last_name='SkyDive',
    email='admin@skydive.fr',
    password_hash=pwd.hash('MotDePassefort!'),
    camera_serials=[],
    is_admin=True,
    is_active=True,
)
db.add(user)
db.commit()
print('Admin créé.')
db.close()
"
```

> Remplacez `admin@skydive.fr` et `MotDePassefort!` par vos propres valeurs.

Connectez-vous ensuite sur `http://192.168.1.39` avec ces identifiants.

---

## Étape 10 — Configurer la détection automatique de caméra (règle udev)

Cette étape permet au PC de détecter une caméra branchée en USB et de lancer l'ingestion automatiquement.

Le script `setup.sh` configure cette étape automatiquement. En cas d'installation manuelle :

### Script MTP/PTP (GoPro, Insta360 MTP, Sony…)

```bash
sudo tee /usr/local/bin/skydive-camera.sh > /dev/null <<'EOF'
#!/bin/bash
LOG=/tmp/skydive-camera.log
MODEL_CLEAN=$(echo "$ID_MODEL" | tr '_' ' ')
echo "[$(date)] udev MTP trigger: serial=$ID_SERIAL_SHORT vendor=$ID_VENDOR_ID model=$MODEL_CLEAN" >> "$LOG"
/usr/bin/systemd-run --no-block \
  /usr/bin/curl -s -X POST http://127.0.0.1:8000/internal/camera-connected \
  -H "Content-Type: application/json" \
  -d "{\"serial\": \"$ID_SERIAL_SHORT\", \"mtp\": true, \"vendor_id\": \"$ID_VENDOR_ID\", \"model_name\": \"$MODEL_CLEAN\"}" >> "$LOG" 2>&1
EOF
sudo chmod +x /usr/local/bin/skydive-camera.sh
```

### Scripts USB Mass Storage (Insta360 en mode stockage, cartes SD…)

L'architecture utilise deux scripts : un trigger léger appelé par udev, et un worker qui attend que l'hôte ait fini de monter le device avant d'appeler le backend.

> **Pourquoi deux scripts ?** udev a un timeout strict. Le worker peut avoir besoin d'attendre jusqu'à 10 secondes que udisks2 monte le device — il est donc exécuté via `systemd-run --no-block`.

```bash
# Trigger udev (appelé directement par la règle)
sudo tee /usr/local/bin/skydive-storage.sh > /dev/null <<'EOF'
#!/bin/bash
LOG=/tmp/skydive-camera.log
echo "[$(date)] udev storage trigger: serial=$ID_SERIAL_SHORT device=$DEVNAME vendor=$ID_VENDOR_ID model=$ID_MODEL" >> "$LOG"
/usr/bin/systemd-run --no-block \
  /usr/local/bin/skydive-storage-worker.sh \
  "$ID_SERIAL_SHORT" "$DEVNAME" "$ID_VENDOR_ID" "$ID_MODEL"
EOF
sudo chmod +x /usr/local/bin/skydive-storage.sh

# Worker (attend le montage, appelle le backend)
sudo tee /usr/local/bin/skydive-storage-worker.sh > /dev/null <<'EOF'
#!/bin/bash
SERIAL="$1"
DEVNAME="$2"
VENDOR_ID="$3"
MODEL=$(echo "$4" | tr '_' ' ')
LOG=/tmp/skydive-camera.log

# Attendre que udisks2 monte le device (max 10s)
MOUNT_PATH=""
for i in $(seq 1 10); do
    MP=$(lsblk -no MOUNTPOINT "$DEVNAME" 2>/dev/null | grep -v '^[[:space:]]*$' | head -1)
    if [ -n "$MP" ]; then MOUNT_PATH="$MP"; break; fi
    sleep 1
done

if [ -n "$MOUNT_PATH" ]; then
    echo "[$(date)] Monté : $DEVNAME → $MOUNT_PATH" >> "$LOG"
    DEVICE_PARAM="$MOUNT_PATH"
else
    echo "[$(date)] Non monté après 10s, fallback: $DEVNAME" >> "$LOG"
    DEVICE_PARAM="$DEVNAME"
fi

/usr/bin/curl -s -X POST http://127.0.0.1:8000/internal/camera-connected \
    -H "Content-Type: application/json" \
    -d "{\"serial\": \"$SERIAL\", \"mtp\": false, \"device_node\": \"$DEVICE_PARAM\", \"vendor_id\": \"$VENDOR_ID\", \"model_name\": \"$MODEL\"}" >> "$LOG" 2>&1
EOF
sudo chmod +x /usr/local/bin/skydive-storage-worker.sh
```

> **Note Insta360 Mass Storage** : ces caméras exposent le serial USB générique `0001`. Le vrai serial unique est extrait automatiquement des métadonnées `.insv` lors de la première ingestion, et le compte utilisateur est mis à jour. Après la première ingestion réussie, chaque caméra est reconnue par son vrai serial.

### Script de débranchement (commun MTP + Mass Storage)

```bash
sudo tee /usr/local/bin/skydive-disconnect.sh > /dev/null <<'EOF'
#!/bin/bash
LOG=/tmp/skydive-camera.log
echo "[$(date)] udev disconnect: serial=$ID_SERIAL_SHORT" >> "$LOG"
/usr/bin/systemd-run --no-block \
  /usr/bin/curl -s -X POST http://127.0.0.1:8000/internal/camera-disconnected \
  -H "Content-Type: application/json" \
  -d "{\"serial\": \"$ID_SERIAL_SHORT\"}" >> "$LOG" 2>&1
EOF
sudo chmod +x /usr/local/bin/skydive-disconnect.sh
```

### Règle udev

```bash
sudo tee /etc/udev/rules.d/99-skydive-camera.rules > /dev/null <<'EOF'
# Branchement — caméras MTP/PTP (GoPro via gphoto2, Sony, etc.)
ACTION=="bind",   SUBSYSTEM=="usb",   ENV{DEVTYPE}=="usb_device", ENV{ID_GPHOTO2}=="1",      RUN+="/usr/local/bin/skydive-camera.sh"
# Branchement — caméras USB Mass Storage (Insta360, cartes SD)
ACTION=="add",    SUBSYSTEM=="block", ENV{ID_BUS}=="usb",         ENV{DEVTYPE}=="partition", RUN+="/usr/local/bin/skydive-storage.sh"
# Débranchement — GoPro HERO (le serial est sur l'interface réseau NCM au remove)
ACTION=="remove", SUBSYSTEM=="net",   ENV{ID_BUS}=="usb",         ENV{ID_VENDOR_ID}=="2672", RUN+="/usr/local/bin/skydive-disconnect.sh"
# Débranchement — Insta360 Mass Storage
ACTION=="remove", SUBSYSTEM=="block", ENV{ID_BUS}=="usb",         ENV{DEVTYPE}=="partition", RUN+="/usr/local/bin/skydive-disconnect.sh"
EOF

sudo udevadm control --reload-rules
```

> **Pourquoi des règles remove différentes par type ?** Au moment d'un `ACTION=remove`, l'événement `usb_device` n'expose pas `ID_SERIAL_SHORT`. Pour GoPro (USB NCM), le serial est disponible sur l'interface réseau (`SUBSYSTEM=net`). Pour Insta360 (Mass Storage), sur la partition block.

---

## Étape 11 — Configurer n8n (ingestion automatique des PDFs Afifly)

n8n est l'outil d'automatisation qui surveille la boîte Gmail et envoie les PDFs Afifly reçus au backend.

Le workflow est automatiquement importé au démarrage de n8n, mais les credentials Gmail doivent être configurés manuellement une seule fois.

### 11.1 — Accéder à n8n

Ouvrir dans un navigateur : `http://192.168.1.39:5678`

Se connecter avec les identifiants définis dans le `.env` (`N8N_USER` / `N8N_PASSWORD`).

### 11.2 — Importer le workflow

1. Dans n8n, cliquer sur **"Add workflow"** → **"Import from file"** (ou via le menu ⋮)
2. Sélectionner le fichier `n8n/workflows/gmail_pdf_afifly.json` présent dans le repo
   > Sur le serveur, ce fichier se trouve dans `~/skydivemediahub/n8n/workflows/gmail_pdf_afifly.json`
3. Le workflow *"gmail PDF Afifly poster"* apparaît dans la liste

### 11.3 — Configurer les credentials Gmail (IMAP)

Le workflow importé est inactif et sans credentials.

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

### 11.4 — Activer le workflow

De retour sur la liste des workflows (`http://192.168.1.39:5678/home/workflows`) :

- Le workflow *"gmail PDF Afifly poster"* doit afficher le statut **Published** (point vert)
- S'il est inactif, cliquer sur les 3 points → **Publish**

Le workflow surveille la boîte Gmail en continu et transmet automatiquement chaque PDF Afifly reçu au backend.

### 11.5 — Tester

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

## Étape 12 — Configurer les notifications email (optionnel)

Les notifications email se configurent depuis l'interface admin, sans redémarrage.

1. Se connecter sur `http://192.168.1.39/admin` (compte admin)
2. Onglet **Paramètres** → section **Notifications email**
3. Renseigner les champs SMTP :

| Champ | Exemple (Gmail) |
|---|---|
| Serveur SMTP | `smtp.gmail.com` |
| Port | `587` |
| Utilisateur | `votre@gmail.com` |
| Mot de passe | App Password Gmail (16 caractères) |
| Adresse expéditeur | `noreply@skydive.fr` |
| URL application | `http://192.168.1.39` |

4. Activer le toggle **"Activer les notifications"**
5. Cliquer **Sauvegarder**

> Si le SMTP n'est pas configuré, l'ingestion fonctionne normalement — aucun email n'est envoyé.

---

## Étape 13 — Mises à jour du code

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
| Interface web | `http://192.168.1.39` |
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
│   │   ├── main.py               # Point d'entrée FastAPI + migrations + scheduler
│   │   ├── auth.py               # JWT : login, middleware, get_current_user
│   │   ├── database.py           # Connexion PostgreSQL / SQLAlchemy
│   │   ├── camera_state.py       # Store in-memory thread-safe (état kiosque temps réel)
│   │   ├── log_buffer.py         # Buffer circulaire des logs backend (500 entrées)
│   │   ├── models/               # Tables : users, rots, rot_participants, videos, settings, cameras
│   │   ├── routers/              # Endpoints API
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── rots.py
│   │   │   ├── videos.py
│   │   │   ├── internal.py       # Déclencheur udev + onboarding caméras inconnues
│   │   │   ├── settings.py
│   │   │   ├── admin_stats.py    # Dashboard monitoring admin
│   │   │   └── cameras.py        # GET /cameras/live (public — kiosque)
│   │   └── services/
│   │       ├── pdf_parser.py     # Parsing PDF Afifly (pdfplumber)
│   │       ├── video_ingestor.py # Ingestion caméra (GoPro HTTP / MTP / block)
│   │       ├── matcher.py        # Matching vidéo ↔ rot par horodatage
│   │       ├── rot_service.py    # Création / upsert des rots en base
│   │       ├── retention.py      # Nettoyage des vidéos expirées (03:00)
│   │       ├── notifier.py       # Notifications email (smtplib STARTTLS)
│   │       └── usb_watcher.py    # Surveillance USB via pyudev (fallback interne)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.jsx              # Point d'entrée React
│   │   ├── App.jsx               # Routage (React Router) — /login, /kiosk, /
│   │   ├── api/client.js         # Instance Axios + intercepteur JWT
│   │   ├── context/AuthContext.jsx
│   │   ├── components/
│   │   │   ├── GestionTab.jsx    # Sous-onglets admin (exports nommés)
│   │   │   └── ProfileTab.jsx
│   │   └── pages/
│   │       ├── LoginPage.jsx     # Connexion + lien "Mode kiosque"
│   │       ├── HomePage.jsx      # Vue principale (onglets : Mes vidéos, Mon compte,
│   │       │                     #   Dashboard, Paramètres serveur, Utilisateurs,
│   │       │                     #   Rotations, Vidéos — les 5 derniers admin only)
│   │       └── KioskPage.jsx     # Page publique /kiosk — suivi ingestion temps réel
│   ├── nginx.conf                # Proxy /api/ + X-Accel-Redirect
│   └── Dockerfile                # Build multi-stage Node 20 → nginx
├── n8n/
│   └── workflows/
│       └── gmail_pdf_afifly.json
├── docker-compose.yml
├── setup.sh                      # Script d'installation automatique
├── .env                          # Configuration locale (jamais committé)
├── README.md                     # Document fonctionnel
└── DEPLOY.md                     # Ce fichier
```

---

## Endpoints API principaux

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | public | Connexion → JWT |
| GET | `/auth/me` | JWT | Profil utilisateur connecté |
| POST | `/users` | admin | Créer un compte sautant |
| PATCH | `/users/{id}/cameras` | admin | Associer des numéros de série caméra |
| POST | `/rots` | admin | Upload PDF Afifly → parse + upsert |
| GET | `/rots` | JWT | Lister toutes les rotations |
| GET | `/rots/{id}` | JWT | Détail d'une rotation |
| GET | `/videos/user/{id}` | JWT | Vidéos d'un sautant |
| GET | `/videos/rot/{id}` | JWT | Toutes les vidéos d'un rot |
| GET | `/videos/{id}/download` | JWT | Téléchargement (X-Accel-Redirect) |
| GET | `/settings` | admin | Lire la configuration |
| PATCH | `/settings` | admin | Modifier la configuration (dont SMTP) |
| POST | `/internal/camera-connected` | public | Déclencheur d'ingestion (udev) |
| POST | `/internal/camera-disconnected` | public | Débranchement USB → retire la card kiosque |
| GET | `/admin/stats` | admin | Métriques système (CPU, RAM, disque, vidéos, users) |
| GET | `/admin/logs` | admin | Logs backend en temps réel (buffer 500 entrées) |
| GET | `/cameras/live` | **public** | État temps réel des caméras en cours d'ingestion (kiosque) |
