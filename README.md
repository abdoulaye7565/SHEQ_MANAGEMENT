# OREZONE QHSE

Application locale offline-first pour la gestion HSE, formations, presence, shifts, badges, EPI, stock, alertes et rapports.

## Installation officielle

La voie officielle pour preparer une version installable est:

```powershell
.\build_exe_orezone_qhse.bat
```

Le paquet final est genere dans:

```text
dist\OREZONE_QHSE_INSTALLABLE.zip
```

Sur une autre machine:

1. Decompresser `OREZONE_QHSE_INSTALLABLE.zip`.
2. Ouvrir le dossier `OREZONE_QHSE`.
3. Double-cliquer sur `installer_orezone_qhse.bat`.
4. Lancer `OREZONE QHSE` depuis le Bureau ou le menu Demarrer.

En version installee, les exports Excel sont stockes dans:

```text
Documents\OREZONE_QHSE\exports
```

La base SQLite est conservee dans:

```text
%LOCALAPPDATA%\Programs\OREZONE_QHSE\data\orezone.db
```

Le module `Parametres` de l'application affiche ces chemins, la version, l'etat de la base et permet de creer une sauvegarde.

## Lancement developpement

### Bibliotheques a installer

Python 3.12 est recommande. SQLite est inclus avec Python, il n'y a rien a installer pour la base locale.

Bibliotheques Python utilisees maintenant:

- `flet==0.84.0`: interface desktop/mobile.

Bibliotheque prevue plus tard pour le module rapports:

- `reportlab==4.4.9`: generation des rapports PDF.

Bibliotheques utilisees pour fabriquer le paquet Windows:

- `pyinstaller`: generation de l'executable.
- `reportlab==4.4.9`: embarque pour les rapports PDF.

Installation:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Pour le module rapports PDF, on installera plus tard:

```powershell
pip install -r requirements-reports.txt
```

Pour preparer une machine de build:

```powershell
pip install -r requirements-build.txt
```

### Demarrer l'application en developpement

```powershell
python main.py
```

Dans cet environnement Codex, le runtime Python fourni contient deja ces bibliotheques.

## Modules principaux

1. Socle technique
2. Referentiels
3. Employes et badges
4. Formations
5. Matrice formation
6. Shifts, breaks et presence
7. EPI et stock
8. Alertes et tableau de bord
9. Rapports PDF
10. Administration
11. Maintenance equipements et action tracker
12. Parametres application

## Notes operationnelles

- SQLite est adapte au fonctionnement offline-first local.
- Pour une utilisation multi-PC avec ecritures simultanees, il faudra definir une vraie strategie de synchronisation.
- Les anciens dossiers `build_*` et `dist_*` sont des artefacts locaux et ne doivent pas etre transferes; seul le ZIP final officiel doit etre utilise.
