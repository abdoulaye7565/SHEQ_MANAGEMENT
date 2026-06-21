# OREZONE QHSE Mobile Offline

## Difference entre les versions

- **OREZONE QHSE Admin** : application Windows principale installee sur le PC administrateur. Elle contient la base centrale, les exports, les parametres, les utilisateurs et le serveur mobile local.
- **OREZONE QHSE Mobile** : application Android terrain. Elle telecharge les donnees utiles, travaille hors connexion, puis synchronise plus tard avec le PC administrateur.

## Demarrage cote PC administrateur

1. Ouvrir OREZONE QHSE Admin.
2. Aller dans `Parametres`.
3. Activer `Serveur local pour application mobile offline`.
4. Generer un token mobile.
5. Demarrer le serveur mobile.
6. Noter l'URL affichee, par exemple `http://192.168.1.20:8765`.

Le telephone doit etre sur le meme reseau Wi-Fi que le PC administrateur au moment du telechargement et de la synchronisation.

## Utilisation cote Android

1. Ouvrir OREZONE QHSE Mobile.
2. Entrer l'URL du serveur PC.
3. Entrer le token mobile.
4. Cliquer `Telecharger`.
5. Travailler hors connexion.
6. Cliquer `Synchroniser` quand le telephone retrouve le reseau du PC.

## Fonctions disponibles dans la premiere version mobile

- Presence offline.
- Toolbox Talk offline avec nombre de participants et commentaire.
- Observation maintenance offline.
- Synchronisation vers le PC administrateur.
- Gestion des telephones appaires dans les parametres PC.
- Blocage d'un telephone depuis le PC administrateur.

## Build Android

### Preparation du PC

Depuis le dossier du projet, double-cliquer sur :

```text
preparer_android_orezone_qhse_mobile.bat
```

Ce script verifie :

- Python du projet.
- Flet.
- Java JDK.

Si Java manque, installer **JDK 17 Windows x64 MSI**, puis relancer le script.

Lien conseille :

```text
https://adoptium.net/temurin/releases/?version=17
```

Un script de telechargement est aussi fourni :

```text
telecharger_jdk17_temurin.bat
```

Il telecharge le JDK dans `downloads`, l'extrait dans `tools`, puis le projet l'utilise comme Java portable. Cette methode evite de modifier Windows si l'installation classique de Java pose probleme.

### Creation de l'APK

Quand la preparation est OK, double-cliquer sur :

```text
build_android_orezone_qhse_mobile.bat
```

Ou lancer depuis PowerShell :

```powershell
.\build_android_orezone_qhse_mobile.ps1
```

Le premier build Android peut demander ou telecharger des composants Android/Gradle selon la machine.

A la fin, le script affiche le chemin du fichier `.apk` cree. Ce fichier est celui a copier sur le telephone Android.

## Securite des telephones

Chaque telephone envoie un `device_id` unique lors de la synchronisation. Le PC administrateur conserve la liste des appareils appaires dans `Parametres`.

Un appareil peut etre :

- `active` : synchronisation autorisee.
- `blocked` : synchronisation refusee.

Si un telephone est perdu ou remplace, le bloquer depuis le PC administrateur.
