# OREZONE QHSE - Cahier des charges fonctionnel mis à jour

**Application de gestion QHSE, employés, formations, présence, TimeSheet, EPI, alertes et rapports**

**Version :** 2.0  
**Date de mise à jour :** 13 mai 2026  
**Technologies :** Python, Flet, SQLite  
**Mode de fonctionnement :** application locale offline-first, desktop Windows

---

## 1. Contexte et justification

OREZONE intervient dans un environnement minier où la sécurité, la conformité réglementaire, la traçabilité des employés et le suivi opérationnel sont essentiels.

L'entreprise a besoin d'un outil interne permettant de centraliser les données QHSE et de réduire les suivis manuels dispersés dans plusieurs fichiers.

L'application OREZONE QHSE répond à ce besoin en proposant une solution locale, installable sur ordinateur Windows, sans serveur externe obligatoire. Elle permet de gérer les employés, les formations, les présences, les shifts, les breaks, les EPI, les alertes et les rapports.

La version actuelle introduit également l'import massif des employés depuis Excel ou CSV, afin d'accélérer la mise en service de la base.

## 2. Objectifs du projet

Les objectifs principaux sont:

- centraliser les informations des employés;
- gérer les badges et les statuts d'accès;
- suivre les présences journalières;
- gérer les shifts, breaks, permissions et maladies;
- produire un TimeSheet mensuel sur une période du 21 au 20;
- suivre les formations, leurs dates d'expiration et la matrice de conformité;
- gérer les EPI, les stocks, les affectations et les inspections;
- générer des alertes automatiques et manuelles;
- produire des rapports Excel et PDF;
- permettre la sauvegarde locale de la base de données;
- faciliter l'installation sur un autre ordinateur;
- offrir un outil exploitable même sans connexion internet après installation.

## 3. Périmètre fonctionnel actuel

La version actuelle couvre les modules suivants:

1. Authentification et première création administrateur.
2. Gestion des rôles et permissions.
3. Référentiels de base.
4. Gestion des employés.
5. Import massif des employés.
6. Gestion des anciens employés.
7. Gestion des présences journalières.
8. Gestion des shifts, breaks, permissions et maladies.
9. TimeSheet mensuel.
10. Gestion des formations.
11. Matrice de formation.
12. Gestion des EPI, stock, affectations et inspections.
13. Alertes QHSE.
14. Tableau de bord.
15. Rapports et exports.
16. Administration, utilisateurs et sauvegardes.

## 4. Acteurs du système

### 4.1 Administrateur

L'administrateur gère:

- les utilisateurs;
- les rôles;
- les référentiels;
- les sauvegardes;
- l'accès complet aux modules.

### 4.2 Officier HSE

L'officier HSE suit:

- les formations;
- la matrice de formation;
- les alertes;
- les rapports QHSE.

### 4.3 Superviseur terrain

Le superviseur terrain suit:

- les employés;
- les présences;
- les breaks;
- le TimeSheet;
- les rapports opérationnels.

### 4.4 Responsable stock

Le responsable stock gère:

- le catalogue EPI;
- les mouvements de stock;
- les affectations EPI;
- les alertes de stock.

### 4.5 Direction

La direction consulte:

- les indicateurs;
- les alertes;
- les rapports consolidés.

## 5. Exigences techniques

### 5.1 Architecture

L'application utilise une architecture locale:

- interface utilisateur avec Flet;
- logique métier en Python;
- base de données SQLite locale;
- fichiers exportés dans un dossier local;
- sauvegardes locales de la base.

### 5.2 Base de données

La base principale est:

```text
data\orezone.db
```

Elle contient notamment:

- les utilisateurs;
- les rôles;
- les employés;
- les badges;
- les présences;
- les breaks;
- les formations;
- les EPI;
- les stocks;
- les alertes;
- les historiques et audits.

### 5.3 Installation

L'application doit pouvoir être installée sur un autre ordinateur Windows en copiant le dossier complet et en installant les dépendances Python.

Un fichier de lancement est prévu:

```text
lancer_orezone_qhse.bat
```

### 5.4 Sauvegarde

L'application doit permettre de créer une copie de sécurité de la base SQLite.

Les sauvegardes sont stockées dans:

```text
backups\
```

## 6. Référentiels

Le module Référentiels doit permettre de gérer les données utilisées par les autres modules:

- sites;
- groupes;
- fonctions;
- shifts;
- types de break;
- types de formation;
- départements de formation;
- types d'EPI;
- rôles.

Les référentiels doivent être vérifiés avant l'import massif des employés, car certaines colonnes d'import doivent correspondre à des valeurs existantes.

## 7. Gestion des employés

### 7.1 Création et modification

Le système doit permettre de créer, modifier, consulter et gérer les employés.

Une fiche employé contient:

- matricule;
- nom;
- prénom;
- nom complet;
- fonction;
- site;
- groupe;
- shift;
- type d'employé;
- statut;
- badge;
- statut du badge;
- date de remise du badge.

### 7.2 Liste des employés

La liste des employés doit permettre:

- la recherche;
- le filtrage par situation, site, fonction, shift et badge;
- la sélection multiple;
- le changement de shift;
- la planification d'un break;
- la remise en service;
- la sortie d'effectif;
- l'export de la liste opérationnelle.

### 7.3 Anciens employés

Lorsqu'un employé quitte l'effectif actif, il doit être conservé dans les anciens employés avec:

- motif de sortie;
- date de sortie;
- commentaire.

L'application doit permettre de restaurer un ancien employé si nécessaire.

## 8. Import massif des employés

### 8.1 Objectif

Le module d'import permet d'ajouter rapidement une liste d'employés depuis un fichier Excel ou CSV.

Formats acceptés:

- `.xlsx`;
- `.csv`.

### 8.2 Modèle d'import

Un modèle Excel est fourni dans:

```text
exports\modele_import_employes_orezone.xlsx
```

Le modèle contient:

- une feuille `Import employes` à remplir;
- une feuille `Exemples`;
- une feuille `Aide`.

### 8.3 Colonnes reconnues

Le fichier peut contenir les colonnes suivantes:

- Matricule;
- Nom;
- Prenom;
- Nom complet;
- Badge;
- Fonction;
- Site;
- Groupe;
- Shift;
- Type employe;
- Statut;
- Statut badge;
- Date remise.

### 8.4 Données obligatoires

Les champs obligatoires sont:

| Champ | Obligatoire | Règle |
| --- | --- | --- |
| Nom + Prenom ou Nom complet | Oui | Il faut identifier l'employé. |
| Fonction | Oui | Doit exister dans les référentiels. |
| Site | Oui | Doit exister dans les référentiels. |
| Shift | Oui | Doit correspondre à un shift connu. |

Valeurs de shift acceptées:

- `DAY`;
- `NIGHT`;
- `Day Shift`;
- `Night Shift`.

### 8.5 Contrôles réalisés avant import

L'application doit vérifier:

- que les champs obligatoires sont renseignés;
- que la fonction existe;
- que le site existe;
- que le groupe existe s'il est renseigné;
- que le shift existe;
- que le matricule n'est pas en doublon;
- que le badge n'est pas en doublon;
- que le type employé est valide;
- que le statut employé est valide;
- que le statut badge est valide.

Si une erreur est détectée, aucun employé ne doit être importé.

L'écran doit afficher les erreurs ligne par ligne.

## 9. Présence journalière

Le module Présence doit permettre:

- de sélectionner une date;
- de générer la liste des employés actifs;
- de marquer un employé présent ou absent;
- de saisir l'heure d'entrée et l'heure de sortie;
- de calculer les heures travaillées;
- de vérifier les anomalies;
- de verrouiller une journée validée;
- de consulter l'audit des modifications;
- d'exporter la présence.

Une journée verrouillée ne peut être modifiée qu'après déverrouillage.

## 10. Breaks, permissions et maladies

Le système doit permettre de planifier:

- break;
- permission;
- maladie.

Chaque période doit contenir:

- employé;
- type;
- date de début;
- date de fin;
- statut;
- commentaire.

Les employés en break, permission ou maladie ne doivent pas apparaître comme employés actifs disponibles dans la présence journalière pendant la période concernée.

## 11. TimeSheet

Le TimeSheet doit couvrir une période mensuelle du 21 au 20.

Exemple:

```text
TimeSheet 2026-04 = du 21/04 au 20/05
```

Le module doit permettre:

- de choisir le mois;
- de définir les jours drilling ou standard;
- de marquer les statuts par employé et par jour;
- de calculer les heures;
- de consulter les totaux;
- de verrouiller le mois;
- de consulter l'audit;
- d'exporter le TimeSheet.

Règles de calcul:

- jour drilling travaillé = 12 heures;
- jour standard travaillé = 8 heures;
- break, permission, maladie ou repos = 0 heure.

## 12. Formations

Le module Formations doit permettre:

- de créer un type de formation;
- de définir une durée de validité;
- d'enregistrer une formation pour un employé;
- de calculer la date d'expiration;
- de mettre à jour une formation existante;
- de gérer les départements responsables;
- de faire des mises à jour groupées;
- d'afficher les formations expirées ou proches de l'expiration.

## 13. Matrice de formation

La matrice doit afficher:

- les employés;
- les types de formation;
- le statut de chaque formation;
- les formations manquantes;
- les formations expirées;
- les formations bientôt expirées;
- les formations valides.

Elle doit permettre une lecture rapide de la conformité formation.

## 14. Gestion des EPI

Le module EPI doit permettre:

- de créer les types EPI;
- de créer les articles EPI;
- de gérer le stock;
- d'enregistrer les mouvements de stock;
- d'affecter un EPI à un employé;
- d'enregistrer les retours;
- de définir les EPI requis par fonction;
- de vérifier la conformité EPI;
- de gérer les inspections;
- de suivre les expirations;
- de produire des alertes.

Une affectation EPI ne doit pas être possible si le stock disponible est insuffisant.

## 15. Alertes QHSE

Le système doit gérer:

- les alertes manuelles;
- les alertes formation;
- les alertes EPI;
- les alertes de stock;
- les badges manquants;
- les dépassements d'heures;
- les anomalies opérationnelles.

Une alerte peut avoir les statuts:

- ouverte;
- traitée;
- ignorée.

Les niveaux d'alerte sont:

- bas;
- moyen;
- haut;
- critique.

## 16. Tableau de bord

Le tableau de bord doit présenter des indicateurs de synthèse:

- effectif;
- présence;
- formations;
- EPI;
- alertes;
- breaks;
- conformité générale.

L'objectif est de donner une vue rapide à l'utilisateur dès l'ouverture de l'application.

## 17. Rapports et exports

L'application doit produire les rapports suivants:

- liste de présence Excel;
- liste de présence PDF;
- synthèse mensuelle présence;
- liste opérationnelle des employés;
- liste des anciens employés;
- employés en break;
- liste des formations;
- matrice formation;
- TimeSheet mensuel;
- inventaire EPI;
- alertes QHSE.

Les exports sont enregistrés dans:

```text
exports\
```

Les fichiers Excel doivent rester exploitables par les équipes opérationnelles.

## 18. Administration

Le module Administration doit permettre:

- de créer un utilisateur;
- de modifier un utilisateur;
- de désactiver un utilisateur;
- de réinitialiser un mot de passe;
- de gérer les rôles;
- de créer une sauvegarde;
- de consulter les sauvegardes.

Le système doit empêcher la désactivation du dernier administrateur actif.

## 19. Sécurité

Les mots de passe doivent être stockés sous forme hashée.

L'application doit:

- refuser un utilisateur inactif;
- limiter les modules visibles selon le rôle;
- protéger le dernier administrateur actif;
- conserver les données localement;
- éviter l'exposition des données à un service externe.

## 20. Sauvegarde et restauration

La base de données doit pouvoir être sauvegardée régulièrement.

Avant chaque import massif, il est recommandé de créer une sauvegarde.

Procédure de restauration manuelle:

1. Fermer l'application.
2. Sauvegarder le fichier actuel `data\orezone.db`.
3. Copier une sauvegarde depuis `backups\`.
4. Renommer la sauvegarde en `orezone.db`.
5. Relancer l'application.

## 21. Installation et déploiement

L'application doit pouvoir être déployée sur un autre ordinateur par copie du dossier projet.

Procédure:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-reports.txt
python main.py
```

Un raccourci Bureau peut être créé vers:

```text
lancer_orezone_qhse.bat
```

## 22. Tests et validation

La version actuelle contient des tests unitaires couvrant notamment:

- administration;
- employés;
- import employés;
- alertes;
- présence;
- TimeSheet;
- formation;
- EPI;
- rapports.

La commande de validation est:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## 23. Évolutions futures

Les évolutions possibles sont:

- conversion du manuel et du cahier des charges en PDF officiel;
- amélioration visuelle des écrans;
- ajout d'un module incidents;
- ajout d'un module audits;
- ajout d'un module inspections terrain;
- synchronisation multi-postes;
- gestion avancée des permissions;
- tableau de bord statistique avancé;
- journal d'activité global;
- export Word/PDF plus structuré.

## 24. Critères d'acceptation

L'application est considérée conforme si:

- elle s'installe sur un ordinateur Windows;
- elle se lance avec `main.py` ou le fichier `.bat`;
- le premier administrateur peut être créé;
- les référentiels peuvent être gérés;
- les employés peuvent être créés manuellement;
- les employés peuvent être importés depuis Excel ou CSV;
- les erreurs d'import sont affichées clairement;
- les présences peuvent être saisies et verrouillées;
- le TimeSheet calcule les heures correctement;
- les formations et la matrice sont exploitables;
- les EPI et stocks sont suivis;
- les alertes sont visibles;
- les rapports sont générés dans `exports`;
- les sauvegardes sont créées dans `backups`;
- les tests automatisés passent.

