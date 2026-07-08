# Licence 2 DIT — Examen Pratique Containers et Virtualisation

**Projet :** Bibliothèque Numérique Microservices
**Durée :** 1 semaine — du 08 Juillet 2026 au 16 Juillet 2026

---

## Contexte général

Le Dakar Institute of Technology (DIT) souhaite moderniser la gestion de sa bibliothèque académique.

Actuellement, la gestion des livres et des emprunts est réalisée de manière **manuelle**, ce qui entraîne plusieurs problèmes :

- Difficulté de suivi des livres
- Absence de statistiques fiables
- Gestion inefficace des emprunts
- Manque d'accès numérique pour les étudiants

Afin de résoudre ces problèmes, la direction du DIT souhaite développer une **plateforme web moderne basée sur une architecture microservices** permettant de gérer l'ensemble des opérations de la bibliothèque.

Vous êtes recruté en tant qu'**équipe DevOps** pour concevoir, développer et automatiser le déploiement de cette application.

---

## Objectifs pédagogiques

Ce projet vise à évaluer votre capacité à :

- Concevoir une architecture **microservices**
- Développer une application **backend API**
- Concevoir une **interface frontend**
- Utiliser **Docker et Docker Compose**
- Mettre en place un pipeline **CI/CD avec Jenkins**
- Gérer un projet avec **Git et GitHub**
- Automatiser le déploiement d'une application

---

## Architecture du projet

L'application doit respecter l'architecture suivante :

- Architecture microservices
- Communication via API REST
- Base de données relationnelle
- Conteneurisation avec Docker
- Orchestration avec Docker Compose
- Pipeline CI/CD avec Jenkins

---

## Technologies autorisées

### Backend
- Spring Boot
- Node.js (Express)
- Django / Django REST
- Flask
- FastAPI

### Frontend
- React
- Angular
- Vue.js
- HTML / CSS / JavaScript

### Base de données
- MySQL
- PostgreSQL

---

## Microservices à implémenter

L'application devra contenir au minimum les fonctionnalités suivantes :

### 1 — Livres

- Ajouter un livre
- Modifier un livre
- Supprimer un livre
- Lister les livres
- Recherche par titre, auteur ou ISBN

### 2 — Utilisateurs

- Création d'utilisateurs
- Liste des utilisateurs
- Gestion des types d'utilisateurs (Étudiant, Professeur et Personnel administratif)
- Consultation du profil utilisateur

### 3 — Emprunts

- Emprunter un livre
- Retourner un livre
- Historique des emprunts

---

## Conteneurisation

Chaque composant de l'application devra être conteneurisé :

- Backend
- Frontend
- Base de données

Chaque microservice backend ou frontend doit posséder son propre **Dockerfile**.

Le projet devra être déployé avec **Docker Compose**.

---

## Pipeline CI/CD

Vous devez mettre en place un pipeline CI/CD avec **Jenkins** permettant :

- Récupération du code depuis GitHub
- Construction de l'application
- Build des images Docker
- Déploiement automatique avec Docker Compose

Le pipeline devra être défini dans un fichier : **`Jenkinsfile`**

---

## Livrables attendus

### 1 — Code source

Code envoyé sur **GitHub**. Le dépôt (repository) doit contenir :

- Code backend
- Code frontend
- Dockerfile backend et Dockerfile frontend
- `docker-compose.yml`
- `Jenkinsfile`

### 2 — Rapport du projet

Document PDF contenant :

- Présentation du projet
- Architecture du système
- Description des microservices
- Explication du pipeline CI/CD
- Captures d'écran de l'application

### 3 — README

Le README doit expliquer :

- Installation du projet
- Lancement avec Docker Compose
- Fonctionnement du pipeline Jenkins
- Structure du projet

---

*Bonne chance à toutes et à tous ! Ce projet vous permettra de démontrer votre capacité à concevoir et déployer une application moderne en utilisant les pratiques Containers et Virtualisation.*
