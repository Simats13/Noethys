#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script d'automatisation de génération de l'exécutable Noethys et de son installateur Windows (.exe).
"""

import os
import sys
import shutil
import subprocess

REP_RACINE = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = os.path.join(REP_RACINE, ".venv", "Scripts", "python.exe")
PYINSTALLER_EXE = os.path.join(REP_RACINE, ".venv", "Scripts", "pyinstaller.exe")
NOETHYS_DIR = os.path.join(REP_RACINE, "noethys")
DIST_DIR = os.path.join(REP_RACINE, "dist", "Noethys")
OUTPUT_DIR = os.path.join(REP_RACINE, "Output")

# Chemins possibles pour Inno Setup Compiler
ISCC_CANDIDATES = [
    r"C:\Users\m.maximin\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Users\m.maximin\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules\innosetup\bin\ISCC.exe",
]

def TrouverISCC():
    for chemin in ISCC_CANDIDATES:
        if os.path.exists(chemin):
            return chemin
    # Recherche dans le PATH
    iscc_path = shutil.which("ISCC.exe") or shutil.which("iscc")
    if iscc_path:
        return iscc_path
    return None

def Etape1_CompilationPyInstaller():
    print("=" * 60)
    print("ETAPE 1 : Compilation de Noethys avec PyInstaller")
    print("=" * 60)
    cmd = [PYINSTALLER_EXE, "--noconfirm", os.path.join(REP_RACINE, "Noethys.spec")]
    print("Exécution de :", " ".join(cmd))
    res = subprocess.run(cmd, cwd=REP_RACINE)
    if res.returncode != 0:
        raise RuntimeError("Erreur lors de la compilation PyInstaller (code: %s)" % res.returncode)
    print("Compilation PyInstaller terminée avec succès.")

def Etape2_SynchronisationRessources():
    print("=" * 60)
    print("ETAPE 2 : Vérification et copie des ressources statiques")
    print("=" * 60)
    cible_static = os.path.join(DIST_DIR, "Static")
    source_static = os.path.join(NOETHYS_DIR, "Static")
    if not os.path.exists(cible_static):
        print("Copie du répertoire Static vers dist/Noethys/Static...")
        shutil.copytree(source_static, cible_static)
    
    # Fichiers racine requis
    for nom in ["Versions.txt", "Licence.txt", "Icone.ico"]:
        src = os.path.join(NOETHYS_DIR, nom)
        dst = os.path.join(DIST_DIR, nom)
        if not os.path.exists(dst) and os.path.exists(src):
            print(f"Copie de {nom} vers {dst}...")
            shutil.copy2(src, dst)

def Etape3_CompilationInstallateur():
    print("=" * 60)
    print("ETAPE 3 : Compilation de l'installateur avec Inno Setup")
    print("=" * 60)
    iscc = TrouverISCC()
    if not iscc:
        raise RuntimeError("Compilateur Inno Setup (ISCC.exe) introuvable !")
    print("Utilisation de ISCC :", iscc)

    # Fermer d'éventuels processus d'installation précédents encore ouverts
    try:
        subprocess.run(["taskkill", "/F", "/IM", "Setup_Noethys*"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/F", "/IM", "Noethys.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    iss_file = os.path.join(REP_RACINE, "installer_noethys.iss")
    cmd = [iscc, iss_file]
    print("Exécution de :", " ".join(cmd))
    
    # Tentatives d'exécution (avec retry si verrouillage temporaire par l'antivirus Windows Defender)
    max_tentatives = 2
    for tentative in range(1, max_tentatives + 1):
        res = subprocess.run(cmd, cwd=REP_RACINE)
        if res.returncode == 0:
            break
        if tentative < max_tentatives:
            print("\n[Avertissement] Échec de compilation (potentiel verrouillage Windows Defender). Nouvelle tentative dans 3 secondes...")
            import time
            time.sleep(3)
        else:
            raise RuntimeError("Erreur lors de la création de l'installateur Inno Setup (code: %s)" % res.returncode)

    print("=" * 60)
    print("SUCCÈS : Installateur généré avec succès !")
    fichiers_out = [os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR) if f.endswith(".exe")]
    for f in fichiers_out:
        taille_mo = os.path.getsize(f) / (1024 * 1024)
        print(f" -> {f} ({taille_mo:.2f} Mo)")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Générateur d'exécutable et installateur Noethys")
    parser.add_argument("--iss-only", "--quick", action="store_true", help="Compile uniquement l'installateur Inno Setup (sans relancer PyInstaller)")
    parser.add_argument("--rebuild", action="store_true", help="Force la recompilation complète PyInstaller")
    args = parser.parse_args()

    try:
        exe_existe = os.path.exists(os.path.join(DIST_DIR, "Noethys.exe"))
        if args.iss_only or (exe_existe and not args.rebuild):
            print("Utilisation des fichiers compilés existants dans dist/Noethys (utilisez --rebuild pour forcer la recompilation PyInstaller).")
        else:
            Etape1_CompilationPyInstaller()
        Etape2_SynchronisationRessources()
        Etape3_CompilationInstallateur()
    except Exception as err:
        print("\nERREUR :", str(err), file=sys.stderr)
        sys.exit(1)
