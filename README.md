# ========================================================
DOCUMENT DE BESOINS FONCTIONNELS
Plateforme d'échange vidéo pour parachutistes
Version 0.4 — Mars 2026
========================================================

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

F03 — À la création du compte, le sautant renseigne ses informations minimales : prénom, nom, adresse email, et valide la correspondance avec l'output d'Afifly

F04 — L'association numéro de série <-> compte sautant
      est persistée pour les branchements futurs
      (reconnaissance automatique dès le 2ème branchement).
F05 - Permettre a l'utilisateur d'associer ou reassocier une caméra sur le pupitre. Cette feature existe pour traiter les cas de nouvelle caméra et de problème d'identification de caméra  existante.


4.2 INGESTION DES VIDÉOS
-------------------------
F05 — Le sautant branche sa caméra au pupitre via câble
      USB (solution principale) ou via lecteur de carte SD
      (solution de repli).

F06 — Le système détecte automatiquement le périphérique
      branché, identifie le propriétaire via le numéro de
      série, et lance l'ingestion automatique des fichiers
      vidéo sans action supplémentaire de l'utilisateur.

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
        - Nom, prénom
        - Niveau (A / B / BPA / C / D)
        - Poids, type de saut

      GROUPES DE FORMATION :
        - Reconstitués en analysant les bordures visuelles
          des cellules du tableau PDF (encadrements
          matérialisant les groupes par séparation
          graphique).
        - Technologie cible : pdfplumber avec analyse
          géométrique des bounding boxes.

F11 — Le système associe automatiquement chaque vidéo
      ingérée à un rot en croisant le timestamp du fichier
      vidéo avec l'heure officielle du rot extraite du PDF,
      dans une fenêtre de tolérance configurable.

      RÈGLES DE MATCHING :
        - 1 seul rot dans la fenêtre  -> association
          automatique
        - Plusieurs rots dans la fenêtre -> statut AMBIGU,
          remonte en interface admin pour correction
          manuelle
        - Aucun rot dans la fenêtre -> statut NON_MATCHÉ,
          remonte en interface admin pour correction
          manuelle

      NOTE : La fenêtre de tolérance est un paramètre
      configurable par le super-admin, à calibrer en phase
      de test (certains sautants enchaînent 1 saut toutes
      les 30 min, d'autres 1 saut toutes les 2h).

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
Aucun point ouvert en suspens à ce stade.


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

  [Caméra USB/SD]
       |
       v
  [Backend Python]  <-->  [PostgreSQL]
       |
       v
  [HDDs SATA : stockage vidéos]
       |
       v
  [Interface Web — phase ultérieure]


8.2 COMPOSANTS BACKEND
-----------------------
Langage     : Python 3.11+
Framework   : FastAPI (API REST légère et performante)
ORM         : SQLAlchemy (abstraction base de données)
Tâches fond : APScheduler (polling Gmail, nettoyage rétention)
PDF parsing : pdfplumber (extraction contenu + géométrie)
USB detect  : pyudev (détection branchement caméra sur Linux)
Email       : Gmail API + OAuth2


8.3 BASE DE DONNÉES
--------------------
Moteur : PostgreSQL 15+

Choix justifié par rapport à SQLite :
  - Accès concurrent fiable (plusieurs appareils simultanés)
  - Outillage visuel (pgAdmin)
  - Migration V2 SaaS sans friction
  - Support natif des tableaux (TEXT[]) et du JSON (JSONB)

Connexion configurée via variable d'environnement :
  DATABASE_URL=postgresql://user:password@localhost:5432/skydivemediahub


8.4 SCHÉMA DES TABLES
----------------------

TABLE : users
  Contient toutes les informations d'un sautant,
  y compris ses caméras associées.

  id               SERIAL PRIMARY KEY
  first_name       TEXT NOT NULL
  last_name        TEXT NOT NULL
  email            TEXT UNIQUE NOT NULL
  password_hash    TEXT NOT NULL
  camera_serials   TEXT[]           -- tableau des numéros de série
  afifly_name      TEXT             -- nom tel qu'il apparaît dans Afifly
                                    -- (pour le matching automatique)
  is_admin         BOOLEAN DEFAULT FALSE
  is_active        BOOLEAN DEFAULT TRUE
  created_at       TIMESTAMP DEFAULT NOW()

  NOTE : camera_serials est un tableau natif PostgreSQL.
  Exemple : '{"SN-GOPRO-12345", "SN-INSTA360-67890"}'
  Permet d'associer plusieurs caméras à un même sautant
  (nouvelle caméra, caméra de remplacement, etc.)


TABLE : rots
  Contient uniquement l'en-tête d'une rotation, tel
  qu'extrait du PDF Afifly. Une ligne par rot.

  id                  SERIAL PRIMARY KEY
  rot_number          INTEGER NOT NULL        -- numéro global (ex : 1631)
  day_number          INTEGER                 -- numéro dans la journée
  rot_date            DATE NOT NULL
  rot_time            TIME NOT NULL           -- heure officielle du rot
  plane_registration  TEXT
  pilot               TEXT
  chef_avion          TEXT
  source_pdf_path     TEXT                    -- chemin du PDF source archivé
  parse_status        TEXT DEFAULT 'OK'       -- OK / ERREUR
  parsed_at           TIMESTAMP DEFAULT NOW()


TABLE : rot_participants
  Contient une ligne par sautant par rot.
  C'est ici que sont stockés le groupe de formation,
  le niveau et les détails individuels de chaque sautant
  pour un rot donné.

  id              SERIAL PRIMARY KEY
  rot_id          INTEGER REFERENCES rots(id) NOT NULL
  user_id         INTEGER REFERENCES users(id)  -- NULL si pas encore matché
                                                -- à un compte sautant
  afifly_name     TEXT NOT NULL               -- nom tel qu'il apparaît dans
                                                -- le PDF (ex : "MARTIN Jules")
                                                -- sert au matching automatique
                                                -- avec users.afifly_name
  level           TEXT                        -- A / B / BPA / C / D
  weight          INTEGER                     -- poids en kg
  jump_type       TEXT                        -- ex : FS4, VRW, AFF...
  group_id        INTEGER                     -- numéro du groupe dans ce rot
                                                -- (1, 2, 3... selon les
                                                -- encadrements du PDF)

  EXEMPLE : rot n°1631 avec 20 sautants = 20 lignes dans
  cette table, toutes liées au même rot_id.

  NOTE : user_id peut être NULL dans deux cas :
    1. Le sautant n'a pas encore de compte sur la plateforme.
    2. Le nom Afifly ne correspond à aucun compte connu.
    Dans les deux cas, le super-admin peut faire le lien
    manuellement.


TABLE : videos
  Contient tous les détails d'un fichier vidéo ingéré,
  ainsi que le résultat du matching avec un rot et un groupe.

  id                SERIAL PRIMARY KEY
  file_name         TEXT NOT NULL
  file_path         TEXT NOT NULL             -- chemin absolu sur le HDD
  file_format       TEXT                      -- MP4, MOV, INSV, etc.
  file_size_bytes   BIGINT
  camera_timestamp  TIMESTAMP NOT NULL        -- horodatage lu sur le fichier
  owner_id          INTEGER REFERENCES users(id)
  rot_id            INTEGER REFERENCES rots(id)  -- NULL si non matché
  group_id          INTEGER                   -- group_id dans le rot (NULL si non matché)
  matching_status   TEXT DEFAULT 'UNMATCHED'  -- MATCHED / AMBIGUOUS / UNMATCHED
  ingested_at       TIMESTAMP DEFAULT NOW()
  expires_at        TIMESTAMP                 -- calculé à l'ingestion selon rétention


TABLE : settings
  Table de configuration système (une seule ligne).
  Modifiable uniquement par le super-admin.

  id                        SERIAL PRIMARY KEY
  retention_days            INTEGER DEFAULT 90
  matching_window_minutes   INTEGER DEFAULT 45   -- à calibrer en phase de test
  video_storage_path        TEXT DEFAULT '/mnt/videos'
  updated_at                TIMESTAMP DEFAULT NOW()


8.5 CONTENEURISATION (DOCKER)
------------------------------
L'ensemble du backend tourne via Docker Compose.
Cela garantit un déploiement identique sur tout PC Ubuntu,
quel que soit le fabricant (Lenovo, HP, Dell, etc.).

  SERVICES DOCKER COMPOSE :

  service : db
    Image     : postgres:15
    Rôle      : base de données PostgreSQL
    Volume    : données persistées sur le disque hôte

  service : backend
    Image     : Python 3.11 (image custom)
    Rôle      : API FastAPI + ingestion USB + polling Gmail
                + parsing PDF + matching
    Mode      : conteneur privilégié (--privileged)
    Volume    : accès au répertoire de stockage vidéo (HDD)

  DÉMARRAGE DU SYSTÈME :
    docker compose up
    (une seule commande, depuis n'importe quelle machine Ubuntu)

  CHOIX DU CONTENEUR PRIVILÉGIÉ POUR L'USB :
    Le conteneur backend tourne en mode privilégié afin
    d'accéder aux périphériques USB via pyudev.
    Ce choix a été retenu car :
      - Le système est local (pas d'exposition internet)
      - Les données sont peu sensibles (vidéos de loisir)
      - Cela évite une configuration udev sur l'hôte et
        maintient toute la logique dans Docker Compose
    Le risque principal (accès accidentel à un mauvais
    périphérique) est mitigé par la précision du code
    d'ingestion sur les périphériques ciblés.


8.6 FLEXIBILITÉ MATÉRIELLE
----------------------------
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
