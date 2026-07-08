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

Créez un compte via `http://localhost/register`. Le rôle `PERSONNEL_ADMIN` donne accès à la gestion des livres et à la liste des utilisateurs ; les rôles `ETUDIANT` et `PROFESSEUR` peuvent emprunter/retourner des livres et consulter leur propre historique.

## Fonctionnement du pipeline Jenkins

Le `Jenkinsfile` définit 4 étapes exécutées dans le conteneur `jenkins` (qui a accès au Docker de l'hôte via `/var/run/docker.sock`) :

1. **Checkout** — récupère le code depuis GitHub.
2. **Build & Test** — installe les dépendances Python de chaque microservice et exécute `pytest`.
3. **Build Docker Images** — `docker compose build`.
4. **Deploy** — `docker compose down && docker compose up -d`.

### Configuration initiale de Jenkins

Jenkins doit être configuré manuellement la première fois :

1. Après `docker compose up -d --build`, récupérez le mot de passe administrateur initial :
   ```bash
   docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```

2. Ouvrez `http://localhost:8080` dans votre navigateur.

3. Collez le mot de passe et terminez l'assistant d'installation (installez les plugins suggérés).

4. Créez un job de type "Pipeline" avec les paramètres suivants :
   - **Definition** : "Pipeline script from SCM"
   - **SCM** : Git
   - **Repository URL** : l'URL de ce dépôt
   - **Script Path** : `Jenkinsfile` (racine du dépôt)

5. Déclenchez une première exécution manuellement via l'interface Jenkins.

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

Mettez à jour la valeur de `group_add` dans `docker-compose.yml` pour le service `jenkins` avec le GID obtenu :

```yaml
services:
  jenkins:
    # ...
    group_add:
      - "YOUR_HOST_DOCKER_GID"
```

Ensuite, redémarrez le conteneur :

```bash
docker compose down
docker compose up -d --build
```

## Limitations connues

L'endpoint interne `PATCH /books/{id}/availability` (utilisé par loans-service pour ajuster le stock lors d'emprunts/retours) n'est protégé que par un JWT valide quelconque et n'est pas restreint aux appels en provenance du service loans uniquement. Tout utilisateur authentifié pourrait théoriquement appeler cet endpoint directement. Une implémentation future pourrait utiliser une authentification inter-services plus robuste (ex : mTLS ou tokens de service dédiés).
