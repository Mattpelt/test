# ========================================================
DOCUMENT DE BESOINS FONCTIONNELS
Plateforme d'échange vidéo pour parachutistes
Version 0.7 — Mars 2026
========================================================

--------------------------------------------------------
DÉPLOIEMENT
--------------------------------------------------------
Installation automatique sur Ubuntu vierge (en SSH) :

  sudo apt install -y git && \
  git clone https://github.com/Mattpelt/test ~/skydivemediahub && \
  bash ~/skydivemediahub/setup.sh

Le script installe Docker, clone le dépôt, génère le .env,
configure la règle udev et démarre l'application.

Documentation complète : voir DEPLOY.md

--------------------------------------------------------
HISTORIQUE DES VERSIONS
--------------------------------------------------------
v0.1 — Version initiale
v0.2 — Correction F09 (récupération autonome PDFs), ajout
        extraction groupes visuels, précision matching timestamp
v0.3 — Clôture des points ouverts PO-1 à PO-6, suppression
        du nom de projet provisoire
v0.4 — Ajout section Architecture Technique (backend, BDD,
        schéma des tables)
v0.5 — Refonte schéma BDD : table rots scindée en rots
        (en-tête) + rot_participants (une ligne par sautant)
v0.6 — Ajout architecture Docker (Compose + conteneur
        privilégié pour détection USB)
v0.7 — État d'avancement session 2 : parser PDF validé,
        ingestion USB/MTP en cours, détail architecture
        détection caméra, API GoPro HTTP confirmée


--------------------------------------------------------
1. CONTEXTE & PROBLÈME
--------------------------------------------------------
Les parachutistes amateurs filment leurs sauts avec des
caméras d'action fixées sur leur casque (GoPro, Insta360,
DJI Osmo, Sony, etc.). Par nature, chaque sautant filme
les autres et non lui-même. L'échange des vidéos après le
saut est fastidieux : incompatibilités entre systèmes
(AirDrop, QuickShare), méconnaissance des outils, perte
de temps en salle de pliage.

L'objectif est d'installer un pupitre physique
(mini-PC + écran) en salle de pliage permettant à chaque
sautant de brancher sa caméra, d'ingérer automatiquement
ses vidéos, et de récupérer celles qui le concernent —
sur place ou à distance via une interface web.


--------------------------------------------------------
2. PÉRIMÈTRE DU MVP
--------------------------------------------------------
- Club pilote : Skydive Pujaut, financé en propre
- Architecture tout en local (le pupitre est le serveur)
- Interface web accessible sur le Wi-Fi local du club
- Le pupitre tourne sous Ubuntu ; l'interface web s'affiche
  en mode kiosque via Chromium (une seule UI pour le pupitre
  et les téléphones des sautants)
- Pas de modèle commercial dans un premier temps
- Migration SaaS multi-clubs envisagée en V2


--------------------------------------------------------
3. RÔLES UTILISATEURS
--------------------------------------------------------
SAUTANT
  Parachutiste membre du club.
  Branche sa caméra au pupitre, reçoit une notification,
  consulte et télécharge ses vidéos.

SUPER-ADMIN
  Administrateur technique.
  Gère les comptes, supervise les anomalies de parsing
  et de matching, configure les paramètres système.
  Préfigure le rôle multi-clubs en V2.


--------------------------------------------------------
4. FONCTIONNALITÉS
--------------------------------------------------------

4.1 ONBOARDING D'UN SAUTANT
----------------------------
F01 — Lors du premier branchement d'une caméra, le système
      détecte automatiquement le numéro de série du
      périphérique et déclenche un flux de création de
      compte.

F02 — Si la détection automatique du numéro de série
      échoue, un login manuel sur l'écran du pupitre
      permet d'identifier le propriétaire et de créer
      son compte.

F03 — À la création du compte, le sautant renseigne ses
      informations minimales : prénom, nom, adresse email,
      et valide la correspondance avec l'output d'Afifly.

F04 — L'association numéro de série <-> compte sautant
      est persistée pour les branchements futurs
      (reconnaissance automatique dès le 2ème branchement).

F05 — Permettre à l'utilisateur d'associer ou réassocier
      une caméra sur le pupitre. Cette feature existe pour
      traiter les cas de nouvelle caméra et de problème
      d'identification de caméra existante.


4.2 INGESTION DES VIDÉOS
-------------------------
F06 — Le sautant branche sa caméra au pupitre via câble
      USB (solution principale). Le système détecte
      automatiquement le périphérique, identifie le
      propriétaire via le numéro de série, et lance
      l'ingestion automatique des fichiers vidéo sans
      action supplémentaire de l'utilisateur.

      NOTE ARCHITECTURE (décision session 2) :
      Les caméras modernes (GoPro, Insta360, Sony)
      ne se montent PAS en mass storage — elles utilisent
      MTP/PTP. Le lecteur de carte SD a été écarté car
      ergonomiquement problématique (confusion entre
      utilisateurs, démontage difficile selon support casque).
      Voir section 8.7 pour le détail de l'architecture
      d'ingestion multi-marques.

F07 — Chaque fichier vidéo ingéré conserve son timestamp
      d'origine (horloge interne de la caméra), qui servira
      à l'association avec un rot.

F08 — Une confirmation visuelle sur l'écran du pupitre
      indique la progression et la fin de l'ingestion
      (nombre de fichiers ingérés, propriétaire identifié).


4.3 RÉCUPÉRATION AUTONOME DES PDFS AFIFLY
------------------------------------------
F09 — Le système surveille en autonomie une boîte Gmail
      dédiée par polling régulier (via Gmail API / OAuth2).
      À chaque nouveau PDF reçu en pièce jointe, il le
      récupère et le traite automatiquement, sans
      intervention humaine. Avec ~30 rotations/jour,
      cette étape est entièrement automatisée.

F10 — Le parser extrait les informations suivantes de
      chaque PDF Afifly :

      EN-TÊTE DU ROT :
        - Numéro de rot global (ex : 1631)
        - Numéro dans la journée (ex : "9 du jour")
        - Date et heure officielle du rot (ex : 16:48)
        - Immatriculation avion, pilote, chef avion

      LISTE DES SAUTANTS :
        - Nom, prénom (avec correction encodage accents)
        - Niveau (A / B / BPA / C / D)
        - Poids, type de saut

      GROUPES DE FORMATION :
        - Détectés par paires de lignes horizontales
          (gap ~5.67pt) dans le PDF pdfplumber.
        - Validé sur 2 PDFs réels (voir section 8.8).

F11 — Le système associe automatiquement chaque vidéo
      ingérée à un rot en croisant le timestamp du fichier
      vidéo avec l'heure officielle du rot extraite du PDF,
      dans une fenêtre de tolérance configurable.

      RÈGLES DE MATCHING :
        - 1 seul rot dans la fenêtre  -> association
          automatique
        - Plusieurs rots dans la fenêtre -> statut AMBIGU,
          remonte en interface admin pour correction manuelle
        - Aucun rot dans la fenêtre -> statut NON_MATCHÉ,
          remonte en interface admin pour correction manuelle

F12 — En cas d'ambiguïté ou d'échec du matching, le
      super-admin peut corriger manuellement l'association
      vidéo <-> rot via l'interface d'administration.


4.4 ACCÈS AUX VIDÉOS POUR LE SAUTANT
--------------------------------------
F13 — Après ingestion et matching, le sautant reçoit une
      notification par email l'informant que ses vidéos
      sont disponibles, avec un lien d'accès direct.

F14 — Le sautant peut télécharger ses vidéos directement
      sur le pupitre (via l'écran en mode kiosque).

F15 — Le sautant peut se connecter à l'interface web
      depuis son téléphone ou ordinateur (Wi-Fi local du
      club) pour consulter et télécharger ses vidéos.

F16 — Le sautant ne voit que les vidéos des sautants
      appartenant à son groupe de formation pour chaque
      rot auquel il a participé, tel que défini par les
      encadrements du PDF Afifly.

F17 — L'interface présente les vidéos organisées par rot
      (date, numéro de rot, numéro dans la journée,
      membres du groupe).


4.5 GESTION & ADMINISTRATION
------------------------------
F18 — Le super-admin consulte et gère les comptes
      sautants : liste, modification, désactivation.

F19 — Le super-admin gère les associations
      caméra <-> sautant : ajout, modification,
      suppression d'un numéro de série.

F20 — Le super-admin supervise le journal des PDFs reçus
      et parsés : statut (succès / échec / ambigu),
      contenu extrait, corrections manuelles possibles.

F21 — Le super-admin configure :
        - La durée de rétention des vidéos (défaut : 3 mois)
        - La fenêtre de tolérance du matching (à calibrer
          en phase de test)

F22 — Le système supprime automatiquement les vidéos dont
      la date d'ingestion dépasse la durée de rétention
      configurée.


--------------------------------------------------------
5. CONTRAINTES & HYPOTHÈSES
--------------------------------------------------------
- Tout fonctionne sur un seul mini-PC Ubuntu (le pupitre
  est le serveur).
- Le réseau local (Wi-Fi club) est hors scope du projet ;
  un Teltonika sera ajouté si nécessaire.
- La plateforme doit fonctionner avec les caméras courantes :
  GoPro, Insta360, DJI Osmo, Sony.
- L'ingestion est agnostique au format vidéo
  (MP4, MOV, INSV...).
- Les horloges des caméras peuvent présenter un léger
  décalage par rapport à l'heure réelle — la fenêtre de
  matching doit en tenir compte.
- Le format des PDFs Afifly est considéré stable
  (généré par Afifly 8.2.x, structure confirmée sur
  2 exemples réels : rot n°1614 et rot n°1631).
- L'accès est limité au réseau local pour le MVP ;
  pas de HTTPS requis à ce stade.


--------------------------------------------------------
6. HORS PÉRIMÈTRE MVP
--------------------------------------------------------
- Transcodage ou assemblage vidéo
- Accès cloud / internet pour les sautants
- Application mobile native
- Modèle de facturation / abonnement
- Gestion multi-clubs
- Reconnaissance des groupes par autre moyen que le PDF


--------------------------------------------------------
7. POINTS OUVERTS RESTANTS
--------------------------------------------------------
Tous les points ouverts initiaux sont fermés.

POINTS OUVERTS SESSION 2 :

PO-7 : Ingestion GoPro via HTTP (Open GoPro API)
  L'API HTTP de la GoPro est confirmée fonctionnelle
  (172.26.166.51:8080/gopro/media/list répond).
  Il faut implémenter le téléchargement HTTP dans
  video_ingestor.py et tester avec des vidéos réelles
  sur la caméra.

PO-8 : Règle udev sur l'hôte Ubuntu
  La détection automatique au branchement nécessite
  une règle udev sur l'hôte (pas dans Docker).
  Voir section 8.7 pour l'architecture cible.

PO-9 : Validation ingestion gphoto2 sur bare-metal
  gphoto2 détecte correctement la caméra dans le
  container mais le transfert PTP échoue en USB/IP
  (latence réseau trop élevée pour le protocole PTP).
  À valider sur le vrai hardware bare-metal.

PO-10 : Moteur de matching vidéo ↔ rot (F11/F12)
PO-11 : Gmail polling + ingestion PDF auto (F09)
PO-12 : Notifications email (F13)
PO-13 : Nettoyage rétention automatique (F22)
PO-14 : Frontend (hors périmètre session actuelle)


========================================================
8. ARCHITECTURE TECHNIQUE
========================================================

PÉRIMÈTRE DE CETTE SECTION
---------------------------
Cette section décrit l'architecture du backend uniquement.
L'interface web (frontend) est hors périmètre de la phase
actuelle de développement.


8.1 VUE D'ENSEMBLE
-------------------
Tout le système tourne sur un seul mini-PC Ubuntu
(format mini-tour, ex : Lenovo ThinkCentre ou HP EliteDesk).
L'architecture est agnostique au fabricant : seul Ubuntu
est requis. Les vidéos sont stockées sur un ou deux HDDs
SATA internes dont le chemin de montage est configurable.

  [Caméra USB]
       |
       v
  [udev HOST] → HTTP POST /internal/camera-connected
       |
       v
  [Backend Python/Docker]  <-->  [PostgreSQL]
       |
       ├── GoPro    → API HTTP Open GoPro (port 8080)
       └── Autres   → gphoto2 (MTP/PTP)
       |
       v
  [HDDs SATA : stockage vidéos]
       |
       v
  [Interface Web — phase ultérieure]


8.2 ENVIRONNEMENT DE DÉVELOPPEMENT
------------------------------------
Développement : PC Windows 11 (Matthieu)
VM de test    : Ubuntu, Hyper-V, IP 192.168.1.97
Repo Git      : https://github.com/Mattpelt/test
Workflow      : commit sur Windows → push GitHub → pull sur VM

Déploiement sur VM :
  cd ~/skydivemediahub && git pull && docker compose up --build -d

API accessible à : http://192.168.1.97:8000
Swagger UI       : http://192.168.1.97:8000/docs


8.3 COMPOSANTS BACKEND
-----------------------
Langage      : Python 3.11+
Framework    : FastAPI (API REST)
ORM          : SQLAlchemy
Tâches fond  : APScheduler (polling Gmail, nettoyage rétention)
PDF parsing  : pdfplumber (extraction contenu + géométrie)
USB detect   : udev HOST → HTTP (voir 8.7)
MTP/PTP      : gphoto2 (caméras non-GoPro)
GoPro        : Open GoPro HTTP API (voir 8.7)
Email        : Gmail API + OAuth2


8.4 BASE DE DONNÉES
--------------------
Moteur : PostgreSQL 15+

Choix justifié par rapport à SQLite :
  - Accès concurrent fiable (plusieurs appareils simultanés)
  - Outillage visuel (pgAdmin)
  - Migration V2 SaaS sans friction
  - Support natif des tableaux (TEXT[]) et du JSON (JSONB)

Connexion configurée via variable d'environnement :
  DATABASE_URL=postgresql://user:password@db:5432/skydivemediahub


8.5 SCHÉMA DES TABLES
----------------------

TABLE : users
  id               SERIAL PRIMARY KEY
  first_name       TEXT NOT NULL
  last_name        TEXT NOT NULL
  email            TEXT UNIQUE NOT NULL
  password_hash    TEXT NOT NULL
  camera_serials   TEXT[]           -- ex: '{"C3491124633666"}'
  afifly_name      TEXT             -- matching avec PDF Afifly
  is_admin         BOOLEAN DEFAULT FALSE
  is_active        BOOLEAN DEFAULT TRUE
  created_at       TIMESTAMP DEFAULT NOW()


TABLE : rots
  id                  SERIAL PRIMARY KEY
  rot_number          INTEGER NOT NULL        -- ex : 1631
  day_number          INTEGER                 -- ex : 9 (du jour)
  rot_date            DATE NOT NULL
  rot_time            TIME NOT NULL
  plane_registration  TEXT                    -- ex : D-IAAI
  pilot               TEXT
  chef_avion          TEXT
  source_pdf_path     TEXT
  parse_status        TEXT DEFAULT 'OK'
  parsed_at           TIMESTAMP DEFAULT NOW()


TABLE : rot_participants
  id              SERIAL PRIMARY KEY
  rot_id          INTEGER REFERENCES rots(id) NOT NULL
  user_id         INTEGER REFERENCES users(id)  -- NULL si non matché
  afifly_name     TEXT NOT NULL
  level           TEXT                        -- A/B/BPA/C/D
  weight          INTEGER
  jump_type       TEXT
  group_id        INTEGER                     -- groupe dans ce rot


TABLE : videos
  id                SERIAL PRIMARY KEY
  file_name         TEXT NOT NULL
  file_path         TEXT NOT NULL
  file_format       TEXT                      -- MP4, MOV, INSV...
  file_size_bytes   BIGINT
  camera_timestamp  TIMESTAMP NOT NULL
  owner_id          INTEGER REFERENCES users(id)
  rot_id            INTEGER REFERENCES rots(id)
  group_id          INTEGER
  matching_status   TEXT DEFAULT 'UNMATCHED'  -- MATCHED/AMBIGUOUS/UNMATCHED
  ingested_at       TIMESTAMP DEFAULT NOW()
  expires_at        TIMESTAMP


TABLE : settings (une seule ligne, initialisée au démarrage)
  id                        SERIAL PRIMARY KEY
  retention_days            INTEGER DEFAULT 90
  matching_window_minutes   INTEGER DEFAULT 45
  video_storage_path        TEXT DEFAULT '/mnt/videos'
  updated_at                TIMESTAMP DEFAULT NOW()


8.6 ENDPOINTS API IMPLÉMENTÉS
-------------------------------

/users
  POST   /users                    — créer un compte
  GET    /users                    — lister tous les sautants actifs
  GET    /users/{id}               — détail d'un sautant
  PATCH  /users/{id}/cameras       — associer numéros de série caméras
  DELETE /users/{id}               — désactiver (soft delete)

/rots
  POST   /rots/debug-pdf           — diagnostic PDF brut (à conserver)
  POST   /rots/parse-preview       — parser PDF sans sauvegarder
  POST   /rots                     — parser PDF et sauvegarder en DB
  GET    /rots                     — lister toutes les rotations
  GET    /rots/{id}                — détail d'une rotation

/videos
  GET    /videos                   — lister toutes les vidéos
  GET    /videos/user/{user_id}    — vidéos d'un sautant
  GET    /videos/{id}              — détail d'une vidéo
  DELETE /videos/{id}              — supprimer une vidéo

/internal
  POST   /internal/camera-connected — déclencheur d'ingestion
                                      (appelé par règle udev hôte)


8.7 ARCHITECTURE DÉTECTION ET INGESTION CAMÉRA
------------------------------------------------

PROBLÈME :
Les caméras modernes (GoPro, Insta360, Sony) ne se montent
pas en USB Mass Storage. Elles utilisent MTP/PTP.
Le lecteur de carte SD a été écarté (ergonomie : confusion
entre utilisateurs, démontage difficile selon support casque).

PROBLÈME DOCKER/NETLINK :
pyudev dans un container Docker ne reçoit pas les events
kernel USB — le socket netlink NETLINK_KOBJECT_UEVENT est
isolé par namespace réseau. Même en conteneur privilégié,
les events ne transitent pas.

SOLUTION RETENUE :
  1. Règle udev sur l'HÔTE Ubuntu détecte le branchement
  2. La règle appelle curl vers l'API du container
  3. L'endpoint /internal/camera-connected déclenche
     l'ingestion dans le container

  Fichier à créer sur l'hôte :
  /etc/udev/rules.d/99-skydive-camera.rules

  Contenu (TODO — PO-8) :
    ACTION=="bind", SUBSYSTEM=="usb", ENV{ID_GPHOTO2}=="1", \
    RUN+="/usr/local/bin/skydive-camera.sh"

  Script /usr/local/bin/skydive-camera.sh :
    #!/bin/bash
    curl -s -X POST http://localhost:8000/internal/camera-connected \
      -H "Content-Type: application/json" \
      -d "{\"serial\": \"$ID_SERIAL_SHORT\", \"mtp\": true}"

DEUX PATHS D'INGESTION :

  PATH A — GoPro (VID=2672) :
    Quand une GoPro se branche, elle crée :
      - Une interface réseau virtuelle USB NCM (enx...)
      - Une interface PTP
    L'hôte reçoit une IP dans le subnet 172.2X.XXX.52/24
    La GoPro est accessible à 172.2X.XXX.51 port 8080
    Endpoints Open GoPro API :
      GET /gopro/media/list     → liste des fichiers
      GET /videos/DCIM/...      → téléchargement
    CONFIRMÉ FONCTIONNEL en test USB/IP (session 2)
    API répond : {"id": "...", "media": [...]}
    À IMPLÉMENTER : video_ingestor.py → ingest_gopro_http()

  PATH B — Autres marques (Insta360, Sony, etc.) :
    gphoto2 via PTP/MTP
    gphoto2 détecte les caméras dans le container ✓
    Le transfert PTP échoue en USB/IP (latence trop élevée)
    SERA VALIDÉ sur bare-metal uniquement
    Déjà implémenté : video_ingestor.py → ingest_mtp_device()

DÉTECTION DU TYPE DE CAMÉRA (dans la règle udev ou l'endpoint) :
  ID_VENDOR_ID=2672 → GoPro → PATH A (HTTP)
  autres            → PATH B (gphoto2)


8.8 PARSER PDF AFIFLY — ÉTAT ET VALIDATION
--------------------------------------------

TECHNOLOGIE :
  pdfplumber avec extract_words() + filtrage par positions x/y.
  La section participants N'EST PAS détectée comme table
  par pdfplumber — on utilise les coordonnées des mots.

COLONNES (coordonnées x en points PDF) :
  Haut.    : x < 57
  Type saut: 57 ≤ x < 165
  Sautant  : 207 ≤ x < 315
  Couleur  : 315 ≤ x < 395
  Poids    : 395 ≤ x < 423

DÉTECTION DES GROUPES :
  Paires de lignes horizontales avec gap ≤ 6.5pt
  = séparateur de groupe. 7 séparateurs = 8 groupes.
  La position y du bas de chaque paire détermine la
  frontière entre groupes.

TOLÉRANCE DE GROUPEMENT DES LIGNES :
  round(top / 5) * 5  (5pt — corrige l'écart de 0.14pt
  entre altitude et nom sur certaines lignes comme CAMBEFORT)

CRITÈRE D'IDENTIFICATION D'UNE LIGNE PARTICIPANT :
  Présence d'un nom dans la colonne Sautant (207-315).
  L'altitude n'est PAS requise (les clients Tandem n'en
  ont pas dans cette colonne).

ENCODAGE :
  Les PDFs Afifly utilisent parfois des bytes UTF-8
  interprétés comme Latin-1 par pdfplumber.
  Correction char par char : si deux chars consécutifs
  ont des byte values formant une séquence UTF-8 valide
  → décoder. Corrige é, à, ê, etc.

VALIDATION SUR PDFs RÉELS :
  rot n°1614 (rot 15 du jour, 29/11/2025) :
    15 participants, 8 groupes — validé ✓
    Tandem : SASSI(client) + ALZIARY(VDO) + BRIERE(moniteur)
    Avant B : TEIXEIRA, BRUCHET, LEBOUCHER,
              JEUNE-RIGOUARD, LEGENDRE (groupes 2-5)
    Saut Classic : CAILLAULT+PASTOUREL, DE ROY+CHAFFARD+
                   BALDUS+CHWALEK, CAMBEFORT (groupes 6-8)

  rot n°1631 (rot 9 du jour, 07/12/2025) :
    9 participants, 3 groupes — validé ✓
    Groupe 1 : SIDERI, CHAFFARD, BRIERE J., LESAGE
    Groupe 2 : GENNESSON, NOEL, ANNABI, STUMPF
    Groupe 3 : BRIERE Tom (solo)


8.9 CONTENEURISATION (DOCKER)
------------------------------

  service : db
    Image     : postgres:15
    Healthcheck: pg_isready toutes les 5s, 10 retries
    Volume    : données persistées sur le disque hôte

  service : backend
    Image     : Python 3.11-slim custom
    Mode      : privileged: true
    Dépend de : db (condition: service_healthy)
    Packages système : udev, libsystemd-dev,
                       libgphoto2-dev, gphoto2
    Packages Python  : voir requirements.txt

  DÉMARRAGE :
    docker compose up --build -d

  VARIABLES D'ENVIRONNEMENT (.env) :
    DATABASE_URL=postgresql://...
    POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    VIDEO_STORAGE_PATH=/mnt/videos


8.10 FLEXIBILITÉ MATÉRIELLE
-----------------------------
Le système est conçu pour fonctionner sur tout PC Ubuntu,
quel que soit le fabricant (Lenovo, HP, Dell, etc.).
Les seuls paramètres matériel-dépendants sont :
  - Le chemin de montage des HDDs (configuré dans settings)
  - Le port réseau local (configuré au niveau Ubuntu/systemd)

Aucun composant logiciel n'est lié à un constructeur.
Docker garantit que les dépendances logicielles sont
identiques d'une machine à l'autre.


========================================================
FIN DU DOCUMENT
========================================================
