# Manuel d'installation et d'utilisation - OREZONE QHSE

## 1. Presentation de l'application

OREZONE QHSE est une application locale pour la gestion QHSE du site OREZONE.

Elle permet de gérer:

- les employés et les badges;
- les anciens employés;
- les présences journalières;
- les breaks, permissions et maladies;
- le TimeSheet mensuel;
- les formations et la matrice de formation;
- les EPI, les stocks et les affectations;
- les alertes QHSE;
- les rapports Excel/PDF;
- les utilisateurs, rôles et sauvegardes.

L'application fonctionne en local sur l'ordinateur. La base de données est un fichier SQLite situé dans:

```text
data\orezone.db
```

## 2. Prérequis

Pour installer l'application sur un ordinateur Windows, il faut:

- Windows 10 ou Windows 11;
- Python 3.12 ou version compatible récente;
- le dossier complet de l'application `QHSE_MANAGEMENT`;
- une connexion internet uniquement pendant l'installation des bibliothèques Python;
- les droits nécessaires pour installer Python et copier le dossier de l'application.

SQLite est inclus avec Python. Il n'y a pas de serveur de base de données à installer.

## 3. Installation sur un nouvel ordinateur

### 3.1 Copier le dossier de l'application

Copier le dossier complet:

```text
C:\xampp\htdocs\QHSE_MANAGEMENT
```

Puis le coller sur le nouvel ordinateur, par exemple ici:

```text
C:\OREZONE_QHSE
```

Le dossier doit contenir au minimum:

```text
app\
data\
docs\
exports\
main.py
requirements.txt
requirements-reports.txt
lancer_orezone_qhse.bat
```

### 3.2 Installer Python

Installer Python depuis le site officiel:

```text
https://www.python.org/downloads/
```

Pendant l'installation, cocher l'option:

```text
Add Python to PATH
```

Pour vérifier l'installation, ouvrir PowerShell et taper:

```powershell
python --version
```

### 3.3 Créer l'environnement virtuel

Ouvrir PowerShell dans le dossier de l'application.

Exemple:

```powershell
cd C:\OREZONE_QHSE
```

Créer l'environnement virtuel:

```powershell
python -m venv .venv
```

Activer l'environnement:

```powershell
.\.venv\Scripts\activate
```

Installer les dépendances:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-reports.txt
```

### 3.4 Lancer l'application

Depuis PowerShell:

```powershell
python main.py
```

Ou double-cliquer sur:

```text
lancer_orezone_qhse.bat
```

### 3.5 Créer un raccourci sur le Bureau

Faire un clic droit sur:

```text
lancer_orezone_qhse.bat
```

Puis choisir:

```text
Envoyer vers > Bureau (créer un raccourci)
```

Renommer le raccourci:

```text
OREZONE QHSE
```

## 4. Première utilisation

Au premier lancement, l'application demande de créer le premier administrateur.

Renseigner:

- le nom d'utilisateur;
- le mot de passe;
- la confirmation du mot de passe.

Le mot de passe doit contenir au moins 8 caractères.

Après création du compte, l'utilisateur est connecté automatiquement.

## 5. Connexion

Au lancement suivant, l'application affiche l'écran de connexion.

Saisir:

- le nom d'utilisateur;
- le mot de passe.

Si l'utilisateur est inactif ou si les identifiants sont incorrects, l'accès est refusé.

## 6. Navigation générale

La navigation principale se trouve sur la gauche de l'écran.

Les modules disponibles dépendent du rôle de l'utilisateur.

Les principaux modules sont:

- Tableau de bord;
- Référentiels;
- Gestion employés;
- Gestion formation;
- TimeSheet;
- Gestion des EPI;
- Alertes;
- Rapports;
- Administration.

## 7. Module Référentiels

Le module Référentiels sert à préparer les données utilisées dans les autres modules.

Avant d'importer ou de créer des employés, vérifier que les référentiels suivants existent:

- Sites;
- Fonctions;
- Groupes;
- Shifts;
- Types de formation;
- Types EPI;
- Rôles.

Les champs `Fonction`, `Site`, `Groupe` et `Shift` utilisés dans les imports doivent correspondre aux valeurs présentes dans ces référentiels.

## 8. Module Gestion employés

Le module Gestion employés regroupe:

- Liste des employés;
- Anciens employés;
- Ajouter un employé;
- Importer;
- Liste de présence;
- Employés en break;
- Breaks et permissions.

### 8.1 Ajouter un employé manuellement

Ouvrir:

```text
Gestion employés > Ajouter un employé
```

Renseigner les informations:

- matricule;
- nom;
- prénom;
- badge;
- fonction;
- site;
- groupe;
- shift;
- type employé;
- statut employé;
- statut badge;
- date de remise du badge.

Cliquer sur:

```text
Ajouter
```

### 8.2 Importer une liste d'employés

Ouvrir:

```text
Gestion employés > Importer
```

Le fichier à importer peut être:

- un fichier CSV;
- un fichier XLSX.

Le modèle recommandé est disponible dans:

```text
exports\modele_import_employes_orezone.xlsx
```

Le modèle contient:

- une feuille `Import employes` à remplir;
- une feuille `Exemples`;
- une feuille `Aide`.

### 8.3 Champs obligatoires pour l'import

Les champs obligatoires sont:

| Champ | Obligatoire | Remarque |
| --- | --- | --- |
| Nom + Prenom ou Nom complet | Oui | Il faut remplir `Nom` et `Prenom`, ou seulement `Nom complet`. |
| Fonction | Oui | Doit exister dans les référentiels. |
| Site | Oui | Doit exister dans les référentiels. |
| Shift | Oui | Valeurs acceptées: `DAY`, `NIGHT`, `Day Shift`, `Night Shift`. |

Les champs optionnels sont:

- Matricule;
- Badge;
- Groupe;
- Type employé;
- Statut;
- Statut badge;
- Date remise.

Attention:

- le matricule ne doit pas être en doublon;
- le badge ne doit pas être en doublon;
- si un groupe est renseigné, il doit exister dans les référentiels;
- ne pas modifier les noms des colonnes dans le modèle.

### 8.4 Procédure d'import

1. Préparer le fichier Excel ou CSV.
2. Ouvrir l'écran `Importer`.
3. Cliquer sur `Parcourir`.
4. Sélectionner le fichier.
5. Cliquer sur `Vérifier`.
6. Corriger les erreurs si nécessaire.
7. Cliquer sur `Importer`.

Si des erreurs sont détectées, aucun employé n'est importé.

L'écran affiche les erreurs ligne par ligne pour faciliter la correction du fichier.

### 8.5 Liste des employés

L'écran `Liste des employés` permet de:

- rechercher un employé;
- filtrer par site, fonction, shift, badge et situation;
- sélectionner plusieurs employés;
- affecter un shift;
- planifier un break;
- remettre en service;
- déclarer une sortie d'effectif;
- exporter la liste des employés.

### 8.6 Anciens employés

Les employés sortis sont conservés dans:

```text
Gestion employés > Anciens employés
```

On peut restaurer un ancien employé si nécessaire.

## 9. Présences

Ouvrir:

```text
Gestion employés > Liste de présence
```

La présence journalière permet de:

- sélectionner une date;
- marquer les employés présents ou absents;
- saisir les heures d'entrée et de sortie;
- calculer les heures travaillées;
- vérifier les anomalies;
- verrouiller la journée;
- exporter la liste.

Une journée verrouillée ne peut plus être modifiée sans déverrouillage.

## 10. Breaks, permissions et maladies

Ouvrir:

```text
Gestion employés > Breaks et permissions
```

Ce module permet de planifier:

- break;
- permission;
- maladie.

Les employés en break ou absence sont exclus des listes de présence actives pendant la période concernée.

L'écran `Employés en break` affiche les employés actuellement concernés.

## 11. Module Formations

Le module Gestion formation permet de:

- enregistrer une formation;
- modifier une formation;
- suivre les dates d'expiration;
- gérer les types de formation;
- gérer les départements responsables;
- consulter la matrice de formation.

La matrice de formation donne une vue globale par employé et par type de formation.

Les formations peuvent être:

- valides;
- bientôt expirées;
- expirées;
- manquantes.

## 12. Module TimeSheet

Le TimeSheet suit une période du 21 au 20 du mois suivant.

Exemple:

```text
TimeSheet 2026-04 = du 21/04 au 20/05
```

Le module permet de:

- sélectionner le mois;
- définir les jours drilling ou non-drilling;
- marquer les jours travaillés, repos, break, permission ou maladie;
- calculer les heures;
- verrouiller le mois;
- consulter l'audit;
- exporter le TimeSheet.

Règles de calcul:

- jour drilling travaillé = 12 heures;
- jour standard travaillé = 8 heures;
- repos, break, permission, maladie = 0 heure.

## 13. Module EPI

Le module Gestion des EPI permet de:

- créer les articles EPI;
- gérer le stock;
- enregistrer les entrées et sorties;
- affecter des EPI aux employés;
- enregistrer les retours;
- définir les EPI requis par fonction;
- suivre la conformité;
- gérer les inspections;
- consulter les alertes de stock ou d'expiration.

Avant d'affecter un EPI, vérifier que le stock disponible est suffisant.

## 14. Module Alertes

Le module Alertes affiche:

- les alertes manuelles;
- les alertes de formation;
- les alertes EPI;
- les badges manquants;
- les anomalies de présence;
- les signaux liés aux breaks.

Les alertes peuvent être:

- ouvertes;
- traitées;
- ignorées.

## 15. Module Rapports

Le module Rapports permet de générer plusieurs exports:

- liste de présence Excel;
- liste de présence PDF;
- synthèse mensuelle présence;
- liste opérationnelle des employés;
- anciens employés;
- employés en break;
- liste des formations;
- matrice formation;
- TimeSheet mensuel;
- inventaire EPI;
- alertes QHSE.

Les fichiers générés sont enregistrés dans:

```text
exports\
```

Si un fichier Excel est ouvert et ne peut pas être remplacé, l'application crée automatiquement un nouveau fichier avec un nom différent.

## 16. Module Administration

Le module Administration permet de:

- créer des utilisateurs;
- modifier les utilisateurs;
- désactiver un utilisateur;
- réinitialiser un mot de passe;
- consulter les rôles;
- créer une sauvegarde de la base;
- consulter les sauvegardes.

L'application empêche de désactiver ou rétrograder le dernier administrateur actif.

## 17. Sauvegarde des données

La base principale se trouve ici:

```text
data\orezone.db
```

Pour sauvegarder les données, utiliser:

```text
Administration > Sauvegarde
```

Les sauvegardes sont enregistrées dans:

```text
backups\
```

Il est recommandé de faire une sauvegarde:

- avant un import massif;
- avant une mise à jour;
- à la fin de chaque semaine;
- avant de copier l'application vers un autre ordinateur.

## 18. Restaurer une sauvegarde

Pour restaurer manuellement une sauvegarde:

1. Fermer l'application.
2. Aller dans le dossier `data`.
3. Renommer le fichier actuel `orezone.db`, par exemple:

```text
orezone_avant_restauration.db
```

4. Copier le fichier de sauvegarde depuis `backups`.
5. Le coller dans `data`.
6. Le renommer:

```text
orezone.db
```

7. Relancer l'application.

## 19. Déplacer l'application vers un autre ordinateur

Pour retrouver les mêmes données sur un autre ordinateur, copier le dossier complet de l'application, y compris:

```text
data\orezone.db
backups\
exports\
```

Puis suivre la procédure d'installation décrite dans la section 3.

## 20. Problèmes fréquents

### 20.1 Python n'est pas reconnu

Message possible:

```text
python n'est pas reconnu
```

Solution:

- réinstaller Python;
- cocher `Add Python to PATH`;
- redémarrer PowerShell.

### 20.2 Les bibliothèques ne sont pas installées

Message possible:

```text
ModuleNotFoundError
```

Solution:

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-reports.txt
```

### 20.3 Le fichier Excel ne s'exporte pas

Cause probable:

- le fichier est déjà ouvert dans Excel.

Solution:

- fermer le fichier Excel;
- relancer l'export;
- vérifier le dossier `exports`.

### 20.4 L'import employé affiche des erreurs

Causes possibles:

- fonction inexistante dans les référentiels;
- site inexistant;
- shift mal écrit;
- matricule en doublon;
- badge en doublon;
- nom/prénom manquant.

Solution:

- corriger le fichier Excel;
- cliquer à nouveau sur `Vérifier`;
- importer uniquement lorsque la vérification est OK.

### 20.5 L'application ne se lance pas avec le raccourci

Vérifier que le raccourci pointe vers:

```text
lancer_orezone_qhse.bat
```

Si le dossier a été déplacé, recréer le raccourci.

## 21. Bonnes pratiques

- Faire une sauvegarde avant chaque import massif.
- Ne pas modifier directement le fichier `data\orezone.db`.
- Ne pas supprimer le dossier `data`.
- Ne pas modifier les noms des colonnes du modèle d'import.
- Vérifier les référentiels avant de créer ou importer des employés.
- Fermer les fichiers Excel avant de générer un nouvel export.
- Utiliser un compte administrateur uniquement pour les opérations sensibles.

## 22. Résumé rapide

Installation:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-reports.txt
python main.py
```

Lancement:

```text
lancer_orezone_qhse.bat
```

Base de données:

```text
data\orezone.db
```

Modèle import employés:

```text
exports\modele_import_employes_orezone.xlsx
```

Sauvegardes:

```text
backups\
```
