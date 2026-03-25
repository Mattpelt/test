# SkyDive Media Hub — Roadmap

> Légende : ✅ Livré · 🔄 En cours · 🐛 Bug · 📋 Planifié · 💡 Idée
> Complexité : `S` < 1h · `M` demi-journée · `L` journée · `XL` plusieurs sessions

---

## ✅ Livré

| # | Feature | Notes |
|---|---------|-------|
| PO-1 | Infrastructure Docker (db, backend, frontend, n8n) | 4 services, privileged backend |
| PO-2 | Parser PDF Afifly | Rotations + groupes, validé sur rot 1614 & 1631 |
| PO-3 | API complète | Auth JWT, CRUD users, vidéos, settings, stats |
| PO-4 | Ingestion GoPro HERO via Open GoPro HTTP API | USB NCM, interface réseau |
| PO-5 | Ingestion Insta360 X5 via USB Mass Storage | udisks2, serial extrait des .insv |
| PO-6 | Architecture udev (4 scripts hôte) | connect MTP/block + disconnect net/block |
| PO-7 | Mode kiosque `/kiosk` | Cards temps réel, SVG caméras, polling 1s |
| PO-8 | Card disparaît au débranchement | Événement udev remove → 10s grace |
| PO-9 | Matching vidéo ↔ rotation | Score delta temporal, fenêtre ±2h |
| PO-10 | Workflow n8n IMAP → PDF Afifly | Gmail → parse → rotations |
| PO-11 | Rétention automatique | APScheduler 03h00, expires_at à l'ingestion |
| PO-12 | Notifications email | SMTP STARTTLS, après ingestion vidéos matchées |
| PO-13 | Frontend complet | Login, kiosk, HomePage (vidéos/compte), admin |
| PO-14 | Onboarding kiosque | Caméra inconnue → "Qui est-ce ?" → nouveau compte ou compte existant |
| PO-15 | Statuts kiosque granulaires | Identification → Connexion → Analyse → Matching → Transfert |
| PO-16 | Contraste WCAG AA | Boost couleurs dark/light pour écrans bas de gamme |

---

## 🐛 Bugs & Corrections rapides

| Priorité | Feature | Description | Complexité |
|----------|---------|-------------|------------|

| ✅ | **Détection auto de la vue desktop/mobile** | Détecter le matériel sur lequel le site est ouvert (mobile ou desktop) et charge automatiquement le mode correspondant. Je ne veux plus de selecteur en haut a droite pour basculer d'un mode a l'autre. Si tu ouvre la page sur mobile => tu as la vue mobile. Idem pour le desktop.| `S` |
| ✅ | **Repositionnement du bouton d'import manuel en mode mobile** | Le bouton d'import manuel est actuellement sous le bouton de téléchargement. Il faudrai le placer en haut a droite du header de la card de la même facon qu'en vue desktop. Pour ca on peut déplacer l'indicateur " x vids" sur la gauche qui est deja dans le header à droite. On obtiendrai sur la première ligne du header : Rot n°X - saut n°Y *(tilté a gauche) puis le reste tilté à droite* Z vidéos  (bouton d'upload) | `S` |

---

## 📋 Features — Court terme

| Priorité | Feature | Description | Complexité |
|----------|---------|-------------|------------|
| ✅ | **Recherche par date dans "Mes vidéos"** | Ajouter un filtre/champ date dans la barre de recherche de la vue Mes vidéos | `S` |
| ✅ | **Import manuel vidéos Insta360 (mobile)** | Permettre à un utilisateur d'importer ses vidéos depuis l'app mobile (vue mobile — RotDropZone dans chaque card rotation) | `M` |
| P1 | **Selection de la destination de stockage des videos** | Permettre a l'admin d'administrer le stockage des vidéos pendant le setup principalement mais aussi pour la maintenance d'une instance | `M` |
| P1 | **Responsivess de la vue mobile** | L'apercu vidéo a déja été corrigé une premiere fois mais s'affiche maintenant en bas à droite de l'écran, seulement 1 quart de la vidéo est visible sans redimenssioner la vue. Le menu déborde et sort de l'écran. Je pense qu'il y a un problème conceptuel sur la vue mobile, on ne devrai meme pas pouvoir zoomer et dezoomer la vue. Ca resemble plus a une page faite pour desktop adaptée en vue portait, mais c'est buggé. J'ai besoin que tu mène un audit de cette vue mobile et que tu propose des amélioration.| `M` |

---

## 💡 Vision — Long terme

| Feature | Description | Complexité |
|---------|-------------|------------|
| **Application mobile** | App dédiée iOS/Android pour consulter ses vidéos, recevoir les notifications, gérer son compte | `XL` |
| **Animations parachutisme** | Animations thématiques (chute libre, ouverture, atterrissage) pendant les temps d'attente kiosque et chargements | `M` |

---

## Notes

- Les items P0 bloquent l'expérience utilisateur → à traiter en priorité
- Les items P1 sont des quick wins à fort impact
- Ce fichier est vivant — ajouter les nouvelles idées au fur et à mesure dans la bonne section
