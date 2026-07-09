# Bibliothèque Numérique Microservices

Plateforme de gestion de bibliothèque pour le DIT, basée sur une architecture microservices (FastAPI + PostgreSQL), un frontend React, une passerelle Nginx, et un pipeline CI/CD Jenkins.

## Architecture

- `users-service` (FastAPI, port interne 8000) — comptes utilisateurs, rôles (`ETUDIANT`, `PROFESSEUR`, `PERSONNEL_ADMIN`), authentification JWT. DB : `users-db` (PostgreSQL).
- `books-service` (FastAPI, port interne 8000) — CRUD livres, recherche, gestion des exemplaires disponibles. DB : `books-db` (PostgreSQL).
- `loans-service` (FastAPI, port interne 8000) — emprunts/retours, historique. Appelle `books-service` en interne. DB : `loans-db` (PostgreSQL).
- `frontend` (React + Vite, servi par Nginx) — interface utilisateur.
- `gateway` (Nginx) — point d'entrée unique sur le port 80, route `/api/auth`, `/api/users`, `/api/books`, `/api/loans` vers le microservice correspondant et `/` vers le frontend.
- `jenkins` — pipeline CI/CD (voir plus bas). Défini dans un fichier Compose séparé (`docker-compose.jenkins.yml`), volontairement en dehors de la stack applicative que le pipeline déploie (voir section Jenkins).

## Installation

**Prérequis :** Docker et Docker Compose uniquement. Node.js et npm ne sont pas nécessaires sur la machine hôte — la construction du frontend et ses dépendances sont gérées dans le Dockerfile du frontend via un build multi-étage.

```bash
git clone <url-du-repo>
cd Examen_Container_Visualisation
```

## Configuration (identifiants et secrets)

Tous les identifiants et secrets (mot de passe PostgreSQL, secret JWT, GID Docker pour Jenkins) sont lus depuis un fichier `.env` à la racine du projet — jamais codés en dur dans `docker-compose.yml`, et `.env` est ignoré par git (voir `.gitignore`).

Des valeurs par défaut sûres pour un usage local/démo sont déjà intégrées dans `docker-compose.yml` (`postgres`/`postgres`, `devsecret`), donc **l'application seule (`docker-compose.yml`) fonctionne sans créer de `.env`**. Jenkins (`docker-compose.jenkins.yml`), en revanche, **requiert un `.env`** avec au minimum `PROJECT_DIR` défini (voir plus bas) — sans quoi il refuse de démarrer. Pour personnaliser (recommandé avant un déploiement réel, et nécessaire pour Jenkins) :

```bash
cp .env.example .env
# puis éditez .env avec vos propres valeurs
```

Variables disponibles (voir `.env.example`) :
- `POSTGRES_USER` / `POSTGRES_PASSWORD` — identifiants partagés par les 3 bases PostgreSQL
- `JWT_SECRET` — secret de signature des JWT, partagé par les 3 microservices
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` — identifiants du premier compte `PERSONNEL_ADMIN`, créé automatiquement au démarrage (voir section Comptes et rôles)
- `DOCKER_GID` — GID du groupe `docker` de la machine hôte (voir section Dépannage)
- `JENKINS_ADMIN_USER` / `JENKINS_ADMIN_PASSWORD` — identifiants du compte administrateur Jenkins, configurés automatiquement au démarrage (voir section Jenkins)
- `REPO_URL` — URL HTTPS du dépôt Git, utilisée pour créer automatiquement le job Pipeline Jenkins (voir section Jenkins)
- `PROJECT_DIR` — **requis pour Jenkins**, chemin absolu de ce dépôt sur la machine hôte (`pwd` depuis la racine du projet). Voir section Jenkins.

## Lancement avec Docker Compose

L'application (bases, microservices, frontend, passerelle) et Jenkins sont deux fichiers Compose distincts, à lancer ensemble :

```bash
docker compose -f docker-compose.yml -f docker-compose.jenkins.yml up -d --build
```

- Application : http://localhost
- Jenkins : http://localhost:8080

Pourquoi deux fichiers plutôt qu'un seul ? Le pipeline Jenkins déploie l'application via `docker compose down && docker compose up -d` (voir section Jenkins) — s'il utilisait le même fichier que celui définissant Jenkins, chaque déploiement tenterait de redémarrer Jenkins lui-même depuis l'intérieur de son propre conteneur, avec des conflits de port quasi garantis. En les séparant, le pipeline ne touche jamais à `docker-compose.jenkins.yml` : `docker compose down`/`up -d` (sans `-f`) n'agissent que sur `docker-compose.yml`, l'application.

Si vous ne voulez lancer que l'application, sans Jenkins :

```bash
docker compose up -d --build
```

Pour arrêter et supprimer les conteneurs (en gardant les données) :

```bash
docker compose -f docker-compose.yml -f docker-compose.jenkins.yml down
```

Pour tout supprimer y compris les volumes de bases de données :

```bash
docker compose -f docker-compose.yml -f docker-compose.jenkins.yml down -v
```

## Comptes et rôles

Créez un compte via `http://localhost/register`. Le formulaire public ne propose que les rôles `ETUDIANT` et `PROFESSEUR` (et l'API rejette explicitement toute tentative de créer un compte `PERSONNEL_ADMIN` par ce biais) — ces deux rôles peuvent emprunter/retourner des livres et consulter leur propre historique.

Le rôle `PERSONNEL_ADMIN` donne accès à la gestion des livres et à la liste des utilisateurs. Un premier compte admin est créé automatiquement au démarrage de `users-service`, avec les identifiants définis par `ADMIN_EMAIL`/`ADMIN_PASSWORD` dans `.env` (par défaut `admin@dit.sn` / `admin123` — **changez ce mot de passe dans `.env` avant tout déploiement réel**). Ce compte n'est créé que si aucun `PERSONNEL_ADMIN` n'existe déjà en base. Pour créer d'autres admins, connectez-vous avec un compte déjà admin et utilisez le bouton « Promouvoir en admin » sur la page Utilisateurs.

## Fonctionnement du pipeline Jenkins

Le `Jenkinsfile` définit 4 étapes exécutées dans le conteneur `jenkins` (qui a accès au Docker de l'hôte via `/var/run/docker.sock`) :

1. **Checkout** — récupère le code depuis GitHub.
2. **Build & Test** — installe les dépendances Python de chaque microservice et exécute `pytest`.
3. **Build Docker Images** — `docker compose build`.
4. **Deploy** — `cd "$PROJECT_DIR" && docker compose down && docker compose up -d`.

Deux détails d'implémentation du **Deploy**, tous deux nécessaires parce que Jenkins pilote le Docker de l'hôte via un socket monté (`/var/run/docker.sock`, docker-outside-of-docker) plutôt que d'avoir son propre Docker isolé :

- Les commandes n'utilisent volontairement pas `-f docker-compose.jenkins.yml` : elles ne redéploient que l'application (`docker-compose.yml`), jamais Jenkins lui-même — sinon chaque déploiement tenterait de redémarrer le conteneur Jenkins qui exécute le pipeline.
- Le `cd "$PROJECT_DIR"` (au lieu du checkout habituel de Jenkins) est nécessaire car le daemon Docker de l'hôte résout les chemins relatifs de `docker-compose.yml` (ex. `./gateway/nginx.conf`) par rapport au répertoire **réel sur l'hôte** depuis lequel `docker compose` est invoqué — pas par rapport à l'espace de travail interne du conteneur Jenkins, qui n'existe pas sur le système de fichiers de l'hôte. `PROJECT_DIR` (variable `.env`, **requise**) est monté dans le conteneur Jenkins au même chemin absolu que sur l'hôte (voir `docker-compose.jenkins.yml`), ce qui permet à `docker compose` d'y résoudre correctement tous les chemins relatifs.

### Configuration initiale de Jenkins

Tout est automatisé via Jenkins Configuration as Code (voir `jenkins/casc.yaml`) : l'assistant d'installation interactif est désactivé, le compte administrateur est créé automatiquement (`JENKINS_ADMIN_USER`/`JENKINS_ADMIN_PASSWORD` dans `.env`, par défaut `admin` / `adminpass123` — **changez ce mot de passe dans `.env` avant tout déploiement réel**), et le job Pipeline `bibliotheque-microservices` est créé automatiquement au démarrage, configuré pour lire le `Jenkinsfile` depuis `REPO_URL` (variable `.env`, doit être une URL HTTPS accessible sans identifiants — dépôt public).

Après `docker compose -f docker-compose.yml -f docker-compose.jenkins.yml up -d --build`, ouvrez `http://localhost:8080`, connectez-vous avec les identifiants ci-dessus, et le job `bibliotheque-microservices` est déjà prêt — aucune configuration manuelle. Il ne reste qu'à déclencher une première exécution ("Build Now") depuis l'interface Jenkins.

## Structure du projet

```
.
├── users-service/       # Microservice utilisateurs + authentification
├── books-service/       # Microservice livres
├── loans-service/       # Microservice emprunts
├── frontend/             # Application React
├── gateway/              # Configuration Nginx (reverse proxy)
├── jenkins/              # Image Jenkins avec Docker CLI
├── docker-compose.yml         # Orchestration de l'application (bases, microservices, frontend, gateway)
├── docker-compose.jenkins.yml # Jenkins, séparé de l'application (voir section Jenkins)
├── Jenkinsfile           # Pipeline CI/CD
├── .env.example          # Modèle des variables d'environnement (identifiants, secrets)
└── docs/                 # Spécification, plan, captures d'écran
```

## Tests

Chaque microservice a sa propre suite de tests `pytest` (base SQLite en mémoire, aucune dépendance à Postgres) :

```bash
cd users-service   # ou books-service / loans-service
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

## Dépannage

### Erreur de permission Docker dans Jenkins

Si vous rencontrez une erreur de permission lors de l'exécution de commandes Docker dans Jenkins (ex : `docker compose exec jenkins docker ps` échoue), vérifiez le GID du groupe `docker` sur votre machine hôte :

```bash
getent group docker
```

Définissez `DOCKER_GID` avec le GID obtenu dans votre fichier `.env` (créez-le depuis `.env.example` si ce n'est pas déjà fait) :

```bash
echo "DOCKER_GID=<gid obtenu ci-dessus>" >> .env
```

Ensuite, redémarrez le conteneur :

```bash
docker compose -f docker-compose.yml -f docker-compose.jenkins.yml down
docker compose -f docker-compose.yml -f docker-compose.jenkins.yml up -d --build
```

## Limitations connues

L'endpoint interne `PATCH /books/{id}/availability` (utilisé par loans-service pour ajuster le stock lors d'emprunts/retours) n'est protégé que par un JWT valide quelconque et n'est pas restreint aux appels en provenance du service loans uniquement. Tout utilisateur authentifié pourrait théoriquement appeler cet endpoint directement. Une implémentation future pourrait utiliser une authentification inter-services plus robuste (ex : mTLS ou tokens de service dédiés).

`PROJECT_DIR` doit correspondre exactement au chemin absolu réel de ce dépôt sur la machine hôte (voir section Jenkins). Si vous déplacez le dépôt après coup, mettez à jour `PROJECT_DIR` dans `.env` et relancez `docker compose -f docker-compose.yml -f docker-compose.jenkins.yml up -d --build` — sinon l'étape `Deploy` du pipeline échouera à nouveau à résoudre les montages relatifs de `docker-compose.yml`.
