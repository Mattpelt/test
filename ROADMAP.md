# SkyDive Media Hub — Roadmap

> Légende : `feat` nouvelle fonctionnalité · `fix` correction de bug · Complexité : `S` <1h · `M` demi-journée · `L` journée · `XL` plusieurs sessions

---

## ✅ Historique

| # | Type | Feature | Notes | Complexité |
|---|------|---------|-------|------------|
| PO-1 | feat | Infrastructure Docker | 4 services, privileged backend | L |
| PO-2 | feat | Parser PDF Afifly | Rotations + groupes, validé sur rot 1614 & 1631 | M |
| PO-3 | feat | API complète | Auth JWT, CRUD users, vidéos, settings, stats | XL |
| PO-4 | feat | Ingestion GoPro HERO via Open GoPro HTTP API | USB NCM, interface réseau | L |
| PO-5 | feat | Ingestion Insta360 X5 via USB Mass Storage | udisks2, serial extrait des .insv | L |
| PO-6 | feat | Architecture udev (4 scripts hôte) | connect MTP/block + disconnect net/block | M |
| PO-7 | feat | Mode kiosque `/kiosk` | Cards temps réel, SVG caméras, polling 1s | L |
| PO-8 | feat | Card disparaît au débranchement | Événement udev remove → 10s grace | S |
| PO-9 | feat | Matching vidéo ↔ rotation | Score delta temporal, fenêtre ±2h | M |
| PO-10 | feat | Workflow n8n IMAP → PDF Afifly | Gmail → parse → rotations | M |
| PO-11 | feat | Rétention automatique | APScheduler 03h00, expires_at à l'ingestion | S |
| PO-12 | feat | Notifications email | SMTP STARTTLS, après ingestion vidéos matchées | M |
| PO-13 | feat | Frontend complet | Login, kiosk, HomePage (vidéos/compte), admin | XL |
| PO-14 | feat | Onboarding kiosque | Caméra inconnue → "Qui est-ce ?" → nouveau compte ou existant | M |
| PO-15 | feat | Statuts kiosque granulaires | Identification → Connexion → Analyse → Matching → Transfert | S |
| PO-16 | feat | Contraste WCAG AA mode sombre | Boost couleurs dark pour écrans bas de gamme | S |
| FEAT-1 | feat | Recherche par date dans "Mes vidéos" | Filtre mois/année via icône calendrier | S |
| FEAT-2 | feat | Import manuel vidéos Insta360 (mobile) | RotDropZone compact dans header card mobile | M |
| FEAT-3 | feat | Filtre par nom de sautant dans "Mes vidéos" | Recherche texte dans la barre de filtre | S |
| FEAT-4 | feat | Vue liste dans "Mes vidéos" | Toggle Par rotation / Liste | S |
| FIX-1 | fix | Détection auto vue desktop/mobile | `matchMedia` réactif, suppression du toggle manuel | S |
| FIX-2 | fix | Repositionnement bouton import en vue mobile | Upload dans header card à droite, compteur déplacé à gauche | S |
| FIX-3 | fix | Contraste mode clair illisible | Fond `#c8d3dc`, bordures `#64748b`, textes near-black | S |
| FIX-4 | fix | Bouton téléchargement inopérant en vue mobile | `document.body.appendChild(a)` avant `.click()` — fix mobile browsers | S |
| FIX-5 | fix | Responsivité vue mobile | Zoom bloqué, overflow corrigé, menu, player en bottom-sheet 95dvh | M |

---

## 📋 Backlog

| # | Priorité | Type | Feature | Description | Complexité |
|---|----------|------|---------|-------------|------------|
| P1.1 | haute | feat | Sélection destination stockage vidéos | Permettre à l'admin de gérer le répertoire de stockage (setup + maintenance) | M |
| VISION-1 | basse | feat | Application mobile | App dédiée iOS/Android — consultation vidéos, notifications, gestion compte | XL |
| VISION-2 | basse | feat | Animations parachutisme | Animation kiosque idle (moutons qui broutent, chute libre…) — générer avant impl. | M |

---

## Notes

- Numérotation : `PO-*` livraison initiale · `FEAT-*` nouvelle fonctionnalité · `FIX-*` correction · `VISION-*` long terme
- Ce fichier est vivant — ajouter les nouvelles idées au fur et à mesure dans la bonne section
