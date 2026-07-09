# Bibliothèque Numérique Microservices

Plateforme de gestion de bibliothèque pour le DIT, basée sur une architecture microservices (FastAPI + PostgreSQL), un frontend React, une passerelle Nginx, et un pipeline CI/CD Jenkins.

## Architecture

- `users-service` (FastAPI, port interne 8000) — comptes utilisateurs, rôles (`ETUDIANT`, `PROFESSEUR`, `PERSONNEL_ADMIN`), authentification JWT. DB : `users-db` (PostgreSQL).
- `books-service` (FastAPI, port interne 8000) — CRUD livres, recherche, gestion des exemplaires disponibles. DB : `books-db` (PostgreSQL).
- `loans-service` (FastAPI, port interne 8000) — emprunts/retours, historique. Appelle `books-service` en interne. DB : `loans-db` (PostgreSQL).
- `frontend` (React + Vite, servi par Nginx) — interface utilisateur.
- `gateway` (Nginx) — point d'entrée unique sur le port 80, route `/api/auth`, `/api/users`, `/api/books`, `/api/loans` vers le microservice correspondant et `/` vers le frontend.
- `jenkins` — pipeline CI/CD (voir plus bas).

## Installation

**Prérequis :** Docker et Docker Compose uniquement. Node.js et npm ne sont pas nécessaires sur la machine hôte — la construction du frontend et ses dépendances sont gérées dans le Dockerfile du frontend via un build multi-étage.

```bash
git clone <url-du-repo>
cd Examen_Container_Visualisation
```

## Configuration (identifiants et secrets)

Tous les identifiants et secrets (mot de passe PostgreSQL, secret JWT, GID Docker pour Jenkins) sont lus depuis un fichier `.env` à la racine du projet — jamais codés en dur dans `docker-compose.yml`, et `.env` est ignoré par git (voir `.gitignore`).

Des valeurs par défaut sûres pour un usage local/démo sont déjà intégrées dans `docker-compose.yml` (`postgres`/`postgres`, `devsecret`, GID `989`), donc **`docker compose up` fonctionne sans créer de `.env`**. Pour personnaliser (recommandé avant un déploiement réel) :

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

## Lancement avec Docker Compose

```bash
docker compose up -d --build
```

- Application : http://localhost
- Jenkins : http://localhost:8080

Pour arrêter et supprimer les conteneurs (en gardant les données) :

```bash
docker compose down
```

Pour tout supprimer y compris les volumes de bases de données :

```bash
docker compose down -v
```

## Comptes et rôles

Créez un compte via `http://localhost/register`. Le formulaire public ne propose que les rôles `ETUDIANT` et `PROFESSEUR` (et l'API rejette explicitement toute tentative de créer un compte `PERSONNEL_ADMIN` par ce biais) — ces deux rôles peuvent emprunter/retourner des livres et consulter leur propre historique.

Le rôle `PERSONNEL_ADMIN` donne accès à la gestion des livres et à la liste des utilisateurs. Un premier compte admin est créé automatiquement au démarrage de `users-service`, avec les identifiants définis par `ADMIN_EMAIL`/`ADMIN_PASSWORD` dans `.env` (par défaut `admin@dit.sn` / `admin123` — **changez ce mot de passe dans `.env` avant tout déploiement réel**). Ce compte n'est créé que si aucun `PERSONNEL_ADMIN` n'existe déjà en base. Pour créer d'autres admins, connectez-vous avec un compte déjà admin et utilisez le bouton « Promouvoir en admin » sur la page Utilisateurs.

## Fonctionnement du pipeline Jenkins

Le `Jenkinsfile` définit 4 étapes exécutées dans le conteneur `jenkins` (qui a accès au Docker de l'hôte via `/var/run/docker.sock`) :

1. **Checkout** — récupère le code depuis GitHub.
2. **Build & Test** — installe les dépendances Python de chaque microservice et exécute `pytest`.
3. **Build Docker Images** — `docker compose build`.
4. **Deploy** — `docker compose down && docker compose up -d`.

### Configuration initiale de Jenkins

L'assistant d'installation interactif est désactivé (Jenkins Configuration as Code, voir `jenkins/casc.yaml`) : Jenkins démarre directement avec un compte administrateur prêt à l'emploi, dont les identifiants viennent de `.env` (`JENKINS_ADMIN_USER`/`JENKINS_ADMIN_PASSWORD`, par défaut `admin` / `adminpass123` — **changez ce mot de passe dans `.env` avant tout déploiement réel**).

1. Après `docker compose up -d --build`, ouvrez `http://localhost:8080` et connectez-vous directement avec ces identifiants (aucun assistant, aucun mot de passe à récupérer dans les logs).

2. Créez un job de type "Pipeline" avec les paramètres suivants :
   - **Definition** : "Pipeline script from SCM"
   - **SCM** : Git
   - **Repository URL** : l'URL de ce dépôt
   - **Script Path** : `Jenkinsfile` (racine du dépôt)

3. Déclenchez une première exécution manuellement via l'interface Jenkins.

La création du job Pipeline lui-même reste une étape manuelle (non automatisée par Configuration as Code dans cette version).

## Structure du projet

```
.
├── users-service/       # Microservice utilisateurs + authentification
├── books-service/       # Microservice livres
├── loans-service/       # Microservice emprunts
├── frontend/             # Application React
├── gateway/              # Configuration Nginx (reverse proxy)
├── jenkins/              # Image Jenkins avec Docker CLI
├── docker-compose.yml    # Orchestration de tous les services
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
docker compose down
docker compose up -d --build
```

## Limitations connues

L'endpoint interne `PATCH /books/{id}/availability` (utilisé par loans-service pour ajuster le stock lors d'emprunts/retours) n'est protégé que par un JWT valide quelconque et n'est pas restreint aux appels en provenance du service loans uniquement. Tout utilisateur authentifié pourrait théoriquement appeler cet endpoint directement. Une implémentation future pourrait utiliser une authentification inter-services plus robuste (ex : mTLS ou tokens de service dédiés).

L'étape `Deploy` du `Jenkinsfile` (`docker compose down && docker compose up -d`) s'exécute depuis le conteneur `jenkins`, qui pilote le daemon Docker de l'hôte via le socket monté `/var/run/docker.sock` (docker-outside-of-docker). Or le répertoire de travail utilisé pour cette commande est un chemin interne au conteneur Jenkins (ex. `/var/jenkins_home/workspace/<job>/...`), qui n'existe pas sur le système de fichiers réel de l'hôte que le daemon utilise pour résoudre les montages relatifs (ex. `./gateway/nginx.conf` dans `docker-compose.yml`). En conséquence, ces montages relatifs peuvent ne pas se résoudre correctement lorsque `docker compose up -d` est lancé de cette manière. Une correction robuste nécessiterait de monter le checkout de l'hôte dans le conteneur Jenkins à un chemin absolu identique (et de configurer le workspace du job Jenkins en conséquence) — hors périmètre pour cet exercice d'une semaine.
