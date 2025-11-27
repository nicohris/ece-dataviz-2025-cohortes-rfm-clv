"""
preprocessing.py
---------------------------------
Pipeline complet de préparation des données
avant analyses (cohortes, RFM, CLV, simulations).

Fonctions principales :
- prepare_base_dataframe()
- filter_customers()
- apply_returns_policy()
- add_derived_variables()
- clean_transactions()
"""

import pandas as pd
import numpy as np


# -------------------------------------------------------------------
# 1. GESTION DES RETOURS
# -------------------------------------------------------------------

def apply_returns_policy(df: pd.DataFrame, mode: str = "include") -> pd.DataFrame:
    """
    Applique la politique de traitement des retours.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset avec colonnes 'quantity' et 'revenue'
    mode : str
        "include"    -> garder retours tels quels
        "exclude"    -> supprimer les lignes où quantity < 0
        "neutralize" -> mettre revenue=0 pour les lignes quantity<0,
                        mais conserver la ligne

    Returns
    -------
    pd.DataFrame
    """
    df = df.copy()
    df["is_return"] = df["quantity"] < 0

    if mode == "include":
        return df

    if mode == "exclude":
        return df.loc[~df["is_return"]].copy()

    if mode == "neutralize":
        df.loc[df["is_return"], "revenue"] = 0
        return df

    raise ValueError("mode doit être dans {include, exclude, neutralize}")


# -------------------------------------------------------------------
# 2. FILTRAGE CLIENTS
# -------------------------------------------------------------------

def filter_customers(df: pd.DataFrame, drop_na=True) -> pd.DataFrame:
    """
    Filtre les clients valides.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset avec 'customer_id'
    drop_na : bool
        True -> exclut les lignes sans customer_id
        False -> conserve tout

    Returns
    -------
    pd.DataFrame
    """
    if drop_na:
        return df[df["customer_id"].notna()].copy()
    return df.copy()


# -------------------------------------------------------------------
# 3. VARIABLES DÉRIVÉES
# -------------------------------------------------------------------

def add_derived_variables(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute revenue, period mensuel, is_return, etc.
    """
    df = df.copy()

    # Timestamp
    df["invoicedate"] = pd.to_datetime(df["invoicedate"])

    # CA ligne
    df["revenue"] = df["quantity"] * df["price"]

    # Indicateurs horaires
    df["year"] = df["invoicedate"].dt.year
    df["month"] = df["invoicedate"].dt.month
    df["invoice_year_month"] = df["invoicedate"].dt.to_period("M")

    # Retours
    df["is_return"] = df["quantity"] < 0

    return df


# -------------------------------------------------------------------
# 4. NETTOYAGE DE BASE
# -------------------------------------------------------------------

def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie les anomalies les plus courantes.
    """
    df = df.copy()

    # Supprime les prix négatifs ou nuls (erreurs)
    df = df[df["price"] > 0]

    # Supprime les quantités nulles
    df = df[df["quantity"] != 0]

    return df


# -------------------------------------------------------------------
# 5. PIPELINE PRINCIPAL
# -------------------------------------------------------------------

def prepare_base_dataframe(
        df_raw: pd.DataFrame,
        drop_customers_na: bool = True,
        returns_policy: str = "include"
) -> pd.DataFrame:
    """
    Pipeline principal combinant :
    - nettoyage
    - variables dérivées
    - filtrage clients
    - gestion retours

    Parameters
    ----------
    df_raw : pd.DataFrame
    drop_customers_na : bool
        Exclure les clients sans ID
    returns_policy : str
        "include" | "exclude" | "neutralize"

    Returns
    -------
    pd.DataFrame
        Données prêtes pour analyses (cohortes, RFM, CLV)
    """

    df = df_raw.copy()

    # Harmoniser colonnes clés (dans certains fichiers UCI : 'Customer ID')
    rename_map = {
        "customer_id": "customer_id",
        "customerid": "customer_id",
        "customer_id ": "customer_id"
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    # Étape 1 – Nettoyage basique
    df = clean_transactions(df)

    # Étape 2 – Variables dérivées
    df = add_derived_variables(df)

    # Étape 3 – Politique retours
    df = apply_returns_policy(df, mode=returns_policy)

    # Étape 4 – Filtrage clients
    df = filter_customers(df, drop_na=drop_customers_na)

    # Final
    df.reset_index(drop=True, inplace=True)

    return df
