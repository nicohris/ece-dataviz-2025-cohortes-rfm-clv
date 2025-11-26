"""
data_loader.py
---------------------------------
Module responsable du chargement brut des données
Online Retail II depuis un fichier Excel (.xlsx).

Fonctions :
- load_raw_excel() : charge et concatène toutes les feuilles
- normalize_columns() : harmonise les noms de colonnes
"""

import pandas as pd
from pathlib import Path


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise les noms de colonnes :
    - strip
    - minuscules
    - remplace espaces / tirets par underscores
    """
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
    return df


def load_raw_excel(filepath: str | Path) -> pd.DataFrame:
    """
    Charge les données Online Retail II
    depuis un fichier Excel contenant plusieurs feuilles.

    Parameters
    ----------
    filepath : str | Path
        Chemin vers le fichier .xlsx

    Returns
    -------
    pd.DataFrame
        Données concaténées de toutes les feuilles disponibles.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Fichier introuvable : {filepath}")

    xls = pd.ExcelFile(filepath)
    frames = []

    for sheet in xls.sheet_names:
        df_sheet = pd.read_excel(xls, sheet_name=sheet)
        df_sheet["source_sheet"] = sheet
        frames.append(df_sheet)

    df_raw = pd.concat(frames, ignore_index=True)
    df_raw = normalize_columns(df_raw)

    return df_raw
