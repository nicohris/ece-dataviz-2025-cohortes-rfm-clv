"""
cohorts.py
---------------------------------
Fonctions pour analyser les cohortes d'acquisition :

- assign_cohort() : ajoute la cohorte d'acquisition à chaque client
- build_retention_table() : table de rétention (cohorte x âge)
- build_revenue_tables() : CA par cohorte et âge + cumul
- compute_avg_revenue_per_age() : revenu moyen par âge de cohorte

Hypothèses :
- df contient au minimum :
  - 'customer_id'
  - 'invoicedate' (datetime)
  - 'revenue' (float)
"""

from __future__ import annotations

from typing import Optional, Tuple

import pandas as pd
from operator import attrgetter


# -------------------------------------------------------------------
# 1. ATTRIBUTION DES COHORTES
# -------------------------------------------------------------------

def assign_cohort(
    df: pd.DataFrame,
    customer_col: str = "customer_id",
    date_col: str = "invoicedate",
    cohort_col: str = "cohort"
) -> pd.DataFrame:
    """
    Assigne une cohorte d'acquisition mensuelle à chaque client.

    - Cohorte = mois de la première transaction du client.
    - Ajoute les colonnes :
        * cohort_col (period[M])
        * order_period (period[M])
        * cohort_index (int, âge de cohorte en mois, 0 = mois d'acquisition)

    Parameters
    ----------
    df : pd.DataFrame
        Données transactionnelles préparées
    customer_col : str
        Nom de la colonne identifiant le client
    date_col : str
        Nom de la colonne de date de transaction
    cohort_col : str
        Nom de la colonne à créer pour la cohorte

    Returns
    -------
    pd.DataFrame
        df enrichi avec cohort, order_period, cohort_index
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    # Période mensuelle de chaque transaction
    df["order_period"] = df[date_col].dt.to_period("M")

    # Mois de la première transaction du client = cohorte
    first_purchase = (
        df.groupby(customer_col)[date_col]
        .min()
        .dt.to_period("M")
    )
    first_purchase.name = cohort_col

    df = df.join(first_purchase, on=customer_col)

    # Âge de cohorte (M+0, M+1, ...)
    df["cohort_index"] = (
        (df["order_period"] - df[cohort_col])
        .apply(attrgetter("n"))
        .astype(int)
    )

    return df


# -------------------------------------------------------------------
# 2. TABLE DE RÉTENTION
# -------------------------------------------------------------------

def build_retention_table(
    df: pd.DataFrame,
    customer_col: str = "customer_id",
    cohort_col: str = "cohort",
    cohort_index_col: str = "cohort_index"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Construit la table de rétention par cohorte.

    Étapes :
    - Nombre de clients actifs par cohorte et âge (M+0, M+1, ...)
    - Taille de cohorte (M+0)
    - Taux de rétention = nb clients actifs / taille cohorte

    Parameters
    ----------
    df : pd.DataFrame
        Données avec colonnes cohort, cohort_index, customer_id
        (par ex. sortie de assign_cohort())
    customer_col : str
    cohort_col : str
    cohort_index_col : str

    Returns
    -------
    retention_table : pd.DataFrame
        index = cohorte, colonnes = âge, valeurs = taux de rétention (float)
    counts_table : pd.DataFrame
        index = cohorte, colonnes = âge, valeurs = nb clients actifs (int)
    """
    # Clients uniques par cohorte et âge
    cohort_data = (
        df.groupby([cohort_col, cohort_index_col])[customer_col]
        .nunique()
        .reset_index()
        .rename(columns={customer_col: "n_customers"})
    )

    # Taille de cohorte = nb clients à M+0
    cohort_sizes = (
        cohort_data[cohort_data[cohort_index_col] == 0]
        .set_index(cohort_col)["n_customers"]
    )

    # Jointure pour obtenir la taille de cohorte sur chaque ligne
    cohort_data = cohort_data.join(
        cohort_sizes,
        on=cohort_col,
        rsuffix="_cohort_size"
    )

    # Taux de rétention
    cohort_data["retention_rate"] = (
        cohort_data["n_customers"]
        / cohort_data["n_customers_cohort_size"]
    )

    # Pivot pour table de rétention
    retention_table = cohort_data.pivot_table(
        index=cohort_col,
        columns=cohort_index_col,
        values="retention_rate"
    ).sort_index(axis=0).sort_index(axis=1)

    counts_table = cohort_data.pivot_table(
        index=cohort_col,
        columns=cohort_index_col,
        values="n_customers"
    ).sort_index(axis=0).sort_index(axis=1)

    return retention_table, counts_table


# -------------------------------------------------------------------
# 3. TABLES DE CA PAR COHORTE
# -------------------------------------------------------------------

def build_revenue_tables(
    df: pd.DataFrame,
    revenue_col: str = "revenue",
    cohort_col: str = "cohort",
    cohort_index_col: str = "cohort_index"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Construit les tables de CA par cohorte et âge de cohorte.

    - revenue_table : CA par cohorte et âge
    - revenue_cum_table : CA cumulé par cohorte et âge

    Parameters
    ----------
    df : pd.DataFrame
        Données avec revenue, cohort, cohort_index
    revenue_col : str
    cohort_col : str
    cohort_index_col : str

    Returns
    -------
    revenue_table : pd.DataFrame
        CA par cohorte et âge
    revenue_cum_table : pd.DataFrame
        CA cumulé par cohorte et âge
    """
    cohort_revenue = (
        df.groupby([cohort_col, cohort_index_col])[revenue_col]
        .sum()
        .reset_index()
    )

    revenue_table = cohort_revenue.pivot_table(
        index=cohort_col,
        columns=cohort_index_col,
        values=revenue_col
    ).sort_index(axis=0).sort_index(axis=1)

    revenue_cum_table = revenue_table.cumsum(axis=1)

    return revenue_table, revenue_cum_table


# -------------------------------------------------------------------
# 4. REVENU MOYEN PAR ÂGE DE COHORTE (CLV EMPIRIQUE)
# -------------------------------------------------------------------

def compute_avg_revenue_per_age(
    revenue_table: pd.DataFrame,
    min_cohort_index: int = 0,
    max_cohort_index: Optional[int] = None
) -> pd.Series:
    """
    Calcule le revenu moyen par âge de cohorte.

    Idée :
    - On prend le tableau CA(cohorte x âge).
    - On restreint à un intervalle d'âges (ex. 0 à 23 mois).
    - On calcule la moyenne du CA (ou du CA moyen par client)
      pour chaque âge de cohorte.

    Exemple simple
    --------------
    Si pour l'âge 0 on a 3 cohortes avec CA [100, 120, 80],
    le revenu moyen à l'âge 0 est (100+120+80)/3 = 100.

    Parameters
    ----------
    revenue_table : pd.DataFrame
        Table CA par cohorte et âge (sortie de build_revenue_tables)
    min_cohort_index : int
        Âge minimum à considérer (par défaut 0 = M+0)
    max_cohort_index : int | None
        Âge maximum à considérer (inclus).
        Si None, utilise la dernière colonne du tableau.

    Returns
    -------
    pd.Series
        index = âge de cohorte, valeurs = revenu moyen à cet âge
    """
    if max_cohort_index is None:
        max_cohort_index = revenue_table.columns.max()

    cols = [c for c in revenue_table.columns
            if min_cohort_index <= c <= max_cohort_index]

    sub = revenue_table[cols]
    avg_per_age = sub.mean(axis=0)

    return avg_per_age
