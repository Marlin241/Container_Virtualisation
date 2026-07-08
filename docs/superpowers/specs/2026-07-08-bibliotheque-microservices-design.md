# Bibliothèque Numérique Microservices — Spec de conception

**Date :** 2026-07-08
**Contexte :** Examen pratique Licence 2 DIT — Containers et Virtualisation (voir `examen_containers_virtualisation.md`)
**Délai :** 08 → 16 juillet 2026

## 1. Objectif

Moderniser la gestion de la bibliothèque du DIT via une plateforme web basée sur une architecture microservices, conteneurisée avec Docker/Docker Compose et déployée automatiquement via un pipeline Jenkins.

## 2. Architecture globale

Trois microservices backend indépendants, chacun avec sa propre base de données PostgreSQL (isolation des données, principe microservices), un frontend React, et une passerelle Nginx qui unifie l'accès.

```
                    ┌─────────────┐
        ┌──────────▶│  frontend   │  (React, servi par Nginx, son propre Dockerfile)
        │           └─────────────┘
┌───────┴───────┐
│    gateway    │  (Nginx officiel + config custom, reverse-proxy)
│  (port 80)    │
└───────┬───────┘
        │  /api/users/*      /api/books/*      /api/loans/*
        ▼                    ▼                  ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ users-service │   │ books-service │◀──│ loans-service │
│   (FastAPI)   │   │   (FastAPI)   │   │   (FastAPI)   │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│   users_db    │   │   books_db    │   │   loans_db    │
│  (postgres)   │   │  (postgres)   │   │  (postgres)   │
└───────────────┘   └───────────────┘   └───────────────┘
```

- Le frontend n'appelle que la passerelle (`/api/...`), jamais directement un microservice → pas de CORS à gérer, topologie interne masquée.
- `loans-service` appelle `books-service` en HTTP interne (nom de conteneur Docker, réseau Compose) pour vérifier/mettre à jour la disponibilité d'un livre lors d'un emprunt/retour.
- Tous les services communiquent sur un réseau Docker Compose privé ; seuls `gateway` (80) et `jenkins` (8080) exposent des ports vers l'hôte.

### Authentification

- `users-service` gère l'inscription et le login, et émet un JWT signé avec un secret partagé (`JWT_SECRET`, variable d'environnement identique sur tous les services).
- `books-service` et `loans-service` valident ce JWT localement (signature + expiration) pour connaître l'identité et le rôle de l'appelant, sans appel réseau supplémentaire à `users-service`.
- Rôles : `ETUDIANT`, `PROFESSEUR`, `PERSONNEL_ADMIN`. Les opérations d'écriture sur les livres (`POST/PUT/DELETE /books`) et la liste globale des utilisateurs sont réservées à `PERSONNEL_ADMIN`.

## 3. Modèles de données & endpoints

### 3.1 `users-service` (DB `users_db`)

**Table `users`**
| Champ | Type | Contrainte |
|---|---|---|
| id | int | PK |
| full_name | string | not null |
| email | string | unique, not null |
| password_hash | string | not null |
| role | enum | ETUDIANT / PROFESSEUR / PERSONNEL_ADMIN |
| created_at | datetime | auto |

**Endpoints**
- `POST /auth/register` — créer un utilisateur (public)
- `POST /auth/login` — vérifie email/mot de passe, retourne `{access_token, token_type}` (JWT contient `sub=user_id`, `role`, `exp`)
- `GET /users` — liste des utilisateurs (PERSONNEL_ADMIN uniquement)
- `GET /users/{id}` — profil d'un utilisateur (soi-même ou PERSONNEL_ADMIN)
- `GET /users/me` — profil de l'utilisateur authentifié (via JWT)

### 3.2 `books-service` (DB `books_db`)

**Table `books`**
| Champ | Type | Contrainte |
|---|---|---|
| id | int | PK |
| title | string | not null |
| author | string | not null |
| isbn | string | unique, not null |
| total_copies | int | ≥ 0 |
| available_copies | int | ≥ 0, ≤ total_copies |
| created_at | datetime | auto |

**Endpoints**
- `POST /books` — ajouter (PERSONNEL_ADMIN)
- `PUT /books/{id}` — modifier (PERSONNEL_ADMIN)
- `DELETE /books/{id}` — supprimer (PERSONNEL_ADMIN)
- `GET /books` — liste
- `GET /books/search?title=&author=&isbn=` — recherche
- `GET /books/{id}` — détail
- `PATCH /books/{id}/availability` — endpoint interne appelé par `loans-service` avec `{delta: -1|+1}` pour décrémenter/incrémenter `available_copies` (retourne 409 si `available_copies` serait négatif)

### 3.3 `loans-service` (DB `loans_db`)

**Table `loans`**
| Champ | Type | Contrainte |
|---|---|---|
| id | int | PK |
| book_id | int | not null (référence logique, pas de FK cross-DB) |
| user_id | int | not null (référence logique) |
| borrowed_at | datetime | auto |
| due_date | datetime | borrowed_at + 14 jours |
| returned_at | datetime | nullable |
| status | enum | EN_COURS / RETOURNE |

**Endpoints**
- `POST /loans` — emprunter `{book_id}` : lit l'identité depuis le JWT, appelle `PATCH books-service/books/{id}/availability {delta:-1}`, crée l'emprunt. Si le livre est indisponible ou introuvable → `409 Conflict`. Si `books-service` est injoignable → `503 Service Unavailable`.
- `PATCH /loans/{id}/return` — retourner : vérifie que l'emprunt est `EN_COURS`, appelle `books-service` avec `{delta:+1}`, marque `RETOURNE` + `returned_at`.
- `GET /loans` — historique. `PERSONNEL_ADMIN` voit tout ; `ETUDIANT`/`PROFESSEUR` voient uniquement leurs propres emprunts (filtré automatiquement via le JWT). Filtre optionnel `?user_id=` (PERSONNEL_ADMIN uniquement).

### 3.4 Gestion des erreurs (principe général)

Pas de transaction distribuée (hors scope) : vérifications séquentielles synchrones entre `loans-service` et `books-service`, avec codes HTTP explicites (`409` incohérence métier, `503` service indisponible) plutôt que des emprunts créés dans un état incohérent.

## 4. Frontend (React)

SPA React consommant uniquement la passerelle (`/api/...`). Pages minimales :
- Login / inscription
- Liste des livres + recherche (titre/auteur/ISBN)
- Formulaire ajout/édition livre (visible si rôle PERSONNEL_ADMIN)
- Liste des utilisateurs (PERSONNEL_ADMIN)
- Profil utilisateur
- Emprunter un livre / retourner un livre / historique des emprunts

Le JWT est stocké côté client (localStorage) et envoyé en `Authorization: Bearer <token>` sur chaque appel API.

## 5. Conteneurisation

- Un `Dockerfile` par microservice backend (`users-service`, `books-service`, `loans-service`) : image Python slim, installe `requirements.txt`, lance `uvicorn`.
- Un `Dockerfile` pour le frontend : build multi-stage (stage 1 `node` build React, stage 2 `nginx` sert les fichiers statiques).
- `gateway/nginx.conf` : configuration Nginx (image officielle `nginx:alpine`, pas de build custom) routant `/` → frontend, `/api/users` → users-service, `/api/books` → books-service, `/api/loans` → loans-service.
- `docker-compose.yml` orchestrant : `users-db`, `books-db`, `loans-db` (postgres:16), `users-service`, `books-service`, `loans-service`, `frontend`, `gateway`, `jenkins`.

## 6. Pipeline CI/CD (Jenkins)

- Jenkins tourne dans un conteneur (`jenkins/jenkins:lts`) avec le CLI Docker installé et `/var/run/docker.sock` monté, pour piloter le Docker de la machine hôte.
- `Jenkinsfile` (pipeline déclaratif), stages :
  1. **Checkout** — récupère le code depuis GitHub
  2. **Build & Test** — installe les dépendances Python de chaque service et lance `pytest` (2-3 tests par service)
  3. **Build Docker Images** — `docker compose build`
  4. **Deploy** — `docker compose down && docker compose up -d`
- Pas de push vers un registre Docker externe : build et déploiement se font localement sur la machine hébergeant Jenkins, suffisant pour la démonstration/l'examen.

## 7. Tests

Tests légers vu le délai d'une semaine, un fichier `tests/` par service avec 2-3 tests pytest couvrant le chemin principal (ex. `users-service` : login réussi/échoué ; `books-service` : création + recherche ; `loans-service` : emprunt puis retour). Objectif : justifier le stage CI "Build & Test", pas une couverture exhaustive.

## 8. Structure du repo

```
Examen_Container_Visualisation/
├── users-service/       (FastAPI, Dockerfile, requirements.txt, tests/)
├── books-service/       (FastAPI, Dockerfile, requirements.txt, tests/)
├── loans-service/       (FastAPI, Dockerfile, requirements.txt, tests/)
├── frontend/             (React, Dockerfile)
├── gateway/              (nginx.conf)
├── docker-compose.yml
├── Jenkinsfile
├── README.md
└── docs/                 (captures d'écran pour le rapport PDF)
```

## 9. Hors scope (volontairement exclu)

- Registre Docker externe (Docker Hub) — build/déploiement 100% locaux via Jenkins.
- Transactions distribuées / saga entre microservices.
- Refresh tokens, réinitialisation de mot de passe, autres flux d'auth avancés.
- Rate limiting, observabilité (logs centralisés, métriques) — non demandés par le sujet.
