# OREZONE QHSE

Application locale offline-first pour la gestion HSE, formations, presence, shifts, badges, EPI, stock, alertes et rapports.

## Lancement

### Bibliotheques a installer

Python 3.12 est recommande. SQLite est inclus avec Python, il n'y a rien a installer pour la base locale.

Bibliotheques Python utilisees maintenant:

- `flet==0.84.0`: interface desktop/mobile.

Bibliotheque prevue plus tard pour le module rapports:

- `reportlab==4.4.9`: generation des rapports PDF.

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

### Demarrer l'application

```powershell
python main.py
```

Dans cet environnement Codex, le runtime Python fourni contient deja ces bibliotheques.

## Modules

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
