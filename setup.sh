#!/bin/bash
# =============================================================
# SkyDive Media Hub — Script d'installation automatique
# Usage : bash setup.sh
# Prérequis : Ubuntu 22.04/24.04, accès sudo
# =============================================================

set -e

# --- Couleurs ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error(){ echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${CYAN}━━━ $1 ━━━${NC}"; }

# --- Vérifications préliminaires ---
[ "$EUID" -eq 0 ] && error "Ne pas lancer ce script en root. Utilisez votre compte utilisateur normal."

command -v sudo &>/dev/null || error "sudo n'est pas disponible."

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     SkyDive Media Hub — Installation         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ==============================================================
# ÉTAPE 1 — Mise à jour système
# ==============================================================
step "1/8 — Mise à jour du système"
sudo apt-get update -qq && sudo apt-get upgrade -y -qq
log "Système à jour"

# ==============================================================
# ÉTAPE 2 — Git
# ==============================================================
step "2/8 — Git"
if command -v git &>/dev/null; then
    log "Git déjà installé ($(git --version))"
else
    sudo apt-get install -y -qq git
    log "Git installé"
fi

# ==============================================================
# ÉTAPE 3 — Docker
# ==============================================================
step "3/8 — Docker"
if command -v docker &>/dev/null; then
    log "Docker déjà installé ($(docker --version))"
else
    sudo apt-get install -y -qq ca-certificates curl gnupg lsb-release

    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    log "Docker installé"
fi

# Ajouter l'utilisateur au groupe docker
if ! groups "$USER" | grep -qw docker; then
    sudo usermod -aG docker "$USER"
    log "Utilisateur '$USER' ajouté au groupe docker"
fi

sudo systemctl enable docker --quiet
log "Docker activé au démarrage"

# ==============================================================
# ÉTAPE 4 — Clonage du dépôt
# ==============================================================
step "4/8 — Dépôt Git"
REPO_BASE="https://github.com/Mattpelt/test"
PROJECT_DIR="$HOME/skydivemediahub"

# Si le script est lancé depuis l'intérieur du dépôt, on reste là
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/docker-compose.yml" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
    log "Dépôt détecté : $PROJECT_DIR"
    git -C "$PROJECT_DIR" pull
elif [ -d "$PROJECT_DIR/.git" ]; then
    log "Dépôt existant, mise à jour..."
    git -C "$PROJECT_DIR" pull
else
    # Tester si le repo est accessible sans authentification
    if git ls-remote "$REPO_BASE" &>/dev/null 2>&1; then
        git clone "$REPO_BASE" "$PROJECT_DIR"
    else
        # Repo privé : demander le Personal Access Token GitHub
        warn "Le dépôt est privé. Un Personal Access Token GitHub est requis."
        echo ""
        echo -e "  Créer un token sur : ${CYAN}https://github.com/settings/tokens${NC}"
        echo -e "  (Settings → Developer settings → Tokens (classic) → Generate, cocher 'repo')"
        echo ""
        read -r -p "  GitHub username : " GH_USER
        read -r -s -p "  Personal Access Token : " GH_TOKEN
        echo ""
        REPO_URL="https://${GH_USER}:${GH_TOKEN}@github.com/Mattpelt/test"
        git clone "$REPO_URL" "$PROJECT_DIR"
        # Supprimer le token de l'URL enregistrée dans git config
        git -C "$PROJECT_DIR" remote set-url origin "$REPO_BASE"
    fi
    log "Dépôt cloné dans $PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# ==============================================================
# ÉTAPE 5 — Fichier .env
# ==============================================================
step "5/8 — Configuration .env"
if [ -f ".env" ]; then
    warn ".env déjà présent — ignoré (supprimez-le pour reconfigurer)"
else
    # Générer un mot de passe aléatoire
    DB_PASS=$(openssl rand -base64 32 | tr -d '/+=\n' | head -c 28)

    # Demander le chemin de stockage vidéo
    echo ""
    echo -e "  Chemin de stockage des vidéos sur ce PC :"
    echo -e "  (Appuyez sur ENTRÉE pour garder ${YELLOW}/mnt/hdd_videos${NC})"
    read -r -p "  > " VIDEO_PATH
    VIDEO_PATH="${VIDEO_PATH:-/mnt/hdd_videos}"

    cat > .env <<EOF
POSTGRES_USER=skydive
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_DB=skydivemediahub
DATABASE_URL=postgresql://skydive:${DB_PASS}@db:5432/skydivemediahub
VIDEO_STORAGE_PATH=${VIDEO_PATH}
EOF

    log ".env créé"
    warn "Mot de passe PostgreSQL généré : ${DB_PASS}"
    warn "Ce mot de passe est stocké dans .env — ne le committez jamais."
fi

# Lire le chemin vidéo depuis .env
VIDEO_PATH=$(grep '^VIDEO_STORAGE_PATH=' .env | cut -d= -f2)

# ==============================================================
# ÉTAPE 6 — Répertoire de stockage vidéo
# ==============================================================
step "6/8 — Répertoire de stockage vidéo"
if [ ! -d "$VIDEO_PATH" ]; then
    sudo mkdir -p "$VIDEO_PATH"
    sudo chown "$USER":"$USER" "$VIDEO_PATH"
    log "Répertoire créé : $VIDEO_PATH"
else
    log "Répertoire existant : $VIDEO_PATH"
fi

# ==============================================================
# ÉTAPE 7 — Règle udev (détection caméra USB)
# ==============================================================
step "7/8 — Règle udev (détection caméra USB)"

# Créer le point de montage pour les caméras USB Mass Storage
sudo mkdir -p /mnt/camera_import

# Script pour caméras MTP/gphoto2 (Insta360 MTP, Sony, etc.)
sudo tee /usr/local/bin/skydive-camera.sh > /dev/null <<'UDEV_SCRIPT'
#!/bin/bash
# Caméras MTP/PTP (gphoto2) — lance curl via systemd pour échapper au timeout udev
LOG=/tmp/skydive-camera.log
echo "[$(date)] udev MTP trigger: serial=$ID_SERIAL_SHORT vendor=$ID_VENDOR_ID" >> "$LOG"
/usr/bin/systemd-run --no-block \
  /usr/bin/curl -s -X POST http://127.0.0.1:8000/internal/camera-connected \
  -H "Content-Type: application/json" \
  -d "{\"serial\": \"$ID_SERIAL_SHORT\", \"mtp\": true, \"vendor_id\": \"$ID_VENDOR_ID\"}" >> "$LOG" 2>&1
UDEV_SCRIPT
sudo chmod +x /usr/local/bin/skydive-camera.sh

# Script pour caméras USB Mass Storage (Insta360, etc.)
sudo tee /usr/local/bin/skydive-storage.sh > /dev/null <<'UDEV_SCRIPT'
#!/bin/bash
# Caméras USB Mass Storage — monte le périphérique puis appelle l'API
LOG=/tmp/skydive-camera.log
MOUNT_POINT=/mnt/camera_import
SERIAL="$ID_SERIAL_SHORT"
DEVNAME_VAR="$DEVNAME"
echo "[$(date)] udev storage trigger: serial=$SERIAL device=$DEVNAME_VAR" >> "$LOG"
/usr/bin/mount "$DEVNAME_VAR" "$MOUNT_POINT" >> "$LOG" 2>&1 && \
/usr/bin/systemd-run --no-block \
  /usr/bin/curl -s -X POST http://127.0.0.1:8000/internal/camera-connected \
  -H "Content-Type: application/json" \
  -d "{\"serial\": \"$SERIAL\", \"mtp\": false, \"device_node\": \"$MOUNT_POINT\"}" >> "$LOG" 2>&1
UDEV_SCRIPT
sudo chmod +x /usr/local/bin/skydive-storage.sh

sudo tee /etc/udev/rules.d/99-skydive-camera.rules > /dev/null <<'UDEV_RULE'
# Caméras MTP/PTP (GoPro via gphoto2, Sony, etc.)
ACTION=="bind", SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ENV{ID_GPHOTO2}=="1", RUN+="/usr/local/bin/skydive-camera.sh"
# Caméras USB Mass Storage (Insta360, etc.)
ACTION=="add", SUBSYSTEM=="block", ENV{ID_BUS}=="usb", ENV{DEVTYPE}=="partition", RUN+="/usr/local/bin/skydive-storage.sh"
UDEV_RULE

sudo udevadm control --reload-rules
log "Règles udev configurées (MTP + USB Mass Storage)"

# ==============================================================
# ÉTAPE 8 — Démarrage Docker Compose
# ==============================================================
step "8/8 — Démarrage de l'application"
sudo docker compose -f "$PROJECT_DIR/docker-compose.yml" up --build -d
log "Application démarrée"

# ==============================================================
# Vérification finale
# ==============================================================
echo ""
step "Vérification"
sleep 4

if sudo docker compose -f "$PROJECT_DIR/docker-compose.yml" ps | grep -q "running"; then
    log "Containers actifs :"
    sudo docker compose -f "$PROJECT_DIR/docker-compose.yml" ps
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN} Installation terminée avec succès !${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  API        : ${CYAN}http://${LOCAL_IP}:8000${NC}"
    echo -e "  Swagger UI : ${CYAN}http://${LOCAL_IP}:8000/docs${NC}"
    echo ""
    echo -e "  Commandes utiles (depuis ~/skydivemediahub) :"
    echo -e "    ${YELLOW}sudo docker compose logs -f backend${NC}          # logs en direct"
    echo -e "    ${YELLOW}sudo docker compose restart backend${NC}          # redémarrer le backend"
    echo -e "    ${YELLOW}git pull && sudo docker compose up --build -d${NC}  # mise à jour"
    echo ""
    echo -e "  Projet : ${PROJECT_DIR}"
    echo ""
else
    error "Un ou plusieurs containers ne sont pas actifs. Vérifiez avec : sudo docker compose -f $PROJECT_DIR/docker-compose.yml logs"
fi
