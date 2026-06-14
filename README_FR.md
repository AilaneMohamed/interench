# Interencheres Public Tracker — Pack Windows EXE

Ce pack te permet de construire une **vraie application Windows `.exe`** pour ton projet, **sans Python installé sur le poste utilisateur**.

## Ce que tu obtiens
- un **launcher desktop** (`launcher.py`) qui démarre l'application ;
- un **build PyInstaller** pour générer `InterencheresPublicTracker.exe` ;
- un **script Windows** prêt à lancer le build : `build_windows_exe.bat` ;
- un **workflow GitHub Actions Windows** pour générer l'EXE automatiquement ;
- le **backend FastAPI** + **frontend web local** ;
- export **CSV / Excel**.

## Résultat attendu après build
Dans le dossier `dist`, tu obtiendras un exécutable du type :

`InterencheresPublicTracker.exe`

L'utilisateur final pourra :
- double-cliquer sur l'exe ;
- l'application ouvrira automatiquement le navigateur sur `http://127.0.0.1:8000` ;
- **aucune installation de Python ne sera nécessaire** sur le poste utilisateur.

---

## Construction du `.exe` sur Windows
### Méthode simple
1. Dézipper ce dossier sur un **PC Windows**.
2. Double-cliquer sur :
   `build_windows_exe.bat`
3. Attendre la fin de compilation.
4. Récupérer l'exécutable dans le dossier :
   `dist\InterencheresPublicTracker.exe`

### Méthode GitHub Actions
1. Ouvrir ce projet dans un dépôt GitHub.
2. Pousser le code.
3. Le workflow `.github/workflows/build-windows-exe.yml` construira automatiquement l'exécutable sur un runner Windows.
4. Télécharger l'artefact généré.

---

## Usage final
L'utilisateur double-clique sur l'exécutable. Le launcher :
1. démarre le serveur local ;
2. attend que le port soit prêt ;
3. ouvre le navigateur automatiquement ;
4. garde l'application en vie tant que l'utilisateur ne ferme pas le process.

---

## Important
- Le **build final `.exe`** doit être fait sur **Windows** (ou via GitHub Actions Windows).
- Les **photos** ne seront récupérées que lorsqu'elles sont **publiquement affichées** sur les pages publiques.
- Les **résultats** ne seront affichés que lorsqu'ils sont **publiquement disponibles**.
- Le code reste configuré pour un usage **sobre**, sans contournement de protections techniques.
