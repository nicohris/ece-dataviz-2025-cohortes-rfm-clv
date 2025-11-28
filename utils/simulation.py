"""
simulation.py
---------------------------------
Fonctions de simulation de scénarios marketing autour de :

- Rétention (r)
- Marge (marge %)
- Remises (rabais sur le CA)
- Politique de retours (inclure / exclure / neutraliser)
- Application globale ou par segment RFM

Ces fonctions sont pensées pour être utilisées dans la page
Streamlit "Scenarios CLV".
"""

from __future__ import annotations

from typing import Optional, Dict, Literal, Tuple

import pandas as pd

from . import clv as clv_mod
from . import preprocessing as prep
from . import rfm as rfm_mod


ReturnsPolicy = Literal["include", "exclude", "neutralize"]


# -------------------------------------------------------------------
# 1. APPLICATION DES REMISES & MARGE
# -------------------------------------------------------------------

def apply_global_discount(
    df: pd.DataFrame,
    discount_pct: float,
    revenue_col: str = "revenue",
    new_col: str = "revenue_after_discount"
) -> pd.DataFrame:
    """
    Applique une remise globale en pourcentage sur le CA.

    Parameters
    ----------
    df : pd.DataFrame
    discount_pct : float
        Pourcentage de remise globale (ex. 0.10 = -10 % sur le CA).
    revenue_col : str
    new_col : str

    Returns
    -------
    pd.DataFrame

    Exemple
    -------
    - revenue = 100
    - discount_pct = 0.1
    -> revenue_after_discount = 90
    """
    df = df.copy()
    factor = 1.0 - discount_pct
    df[new_col] = df[revenue_col] * factor
    return df


def apply_segment_discounts(
    df: pd.DataFrame,
    segment_col: str = "segment_label",
    revenue_col: str = "revenue",
    segment_discounts: Optional[Dict[str, float]] = None,
    default_discount: float = 0.0,
    new_col: str = "revenue_after_discount"
) -> pd.DataFrame:
    """
    Applique des remises différenciées par segment RFM.

    Parameters
    ----------
    df : pd.DataFrame
        Doit contenir segment_col et revenue_col.
    segment_col : str
    revenue_col : str
    segment_discounts : dict | None
        Mapping {segment_label: discount_pct}
        ex. {"Champions": 0.05, "À risque": 0.15}
    default_discount : float
        Remise par défaut si le segment n'est pas dans le mapping.
    new_col : str

    Returns
    -------
    pd.DataFrame
    """
    df = df.copy()

    if segment_discounts is None:
        segment_discounts = {}

    def _get_discount(seg: str) -> float:
        return segment_discounts.get(seg, default_discount)

    discounts = df[segment_col].map(_get_discount)
    df[new_col] = df[revenue_col] * (1.0 - discounts)

    return df


def compute_margin_column(
    df: pd.DataFrame,
    revenue_col: str = "revenue",
    margin_rate: float = 0.3,
    new_col: str = "margin"
) -> pd.DataFrame:
    """
    Calcule la marge à partir d'un taux de marge constant.

    Parameters
    ----------
    df : pd.DataFrame
    revenue_col : str
    margin_rate : float
        ex. 0.3 = 30% de marge
    new_col : str

    Returns
    -------
    pd.DataFrame
    """
    df = df.copy()
    df[new_col] = df[revenue_col] * margin_rate
    return df


# -------------------------------------------------------------------
# 2. KPIs DE BASELINE / SCÉNARIO
# -------------------------------------------------------------------

def aggregate_kpis(
    df: pd.DataFrame,
    revenue_col: str = "revenue",
    margin_col: Optional[str] = None,
    customer_col: str = "customer_id"
) -> dict:
    """
    Agrège quelques KPIs globaux :

    - CA total
    - Marge totale (si margin_col est fourni)
    - Nombre de clients uniques
    - Panier moyen = CA total / nb clients uniques

    Returns
    -------
    dict
    """
    total_revenue = df[revenue_col].sum()
    n_customers = df[customer_col].nunique()

    avg_revenue_per_customer = (
        total_revenue / n_customers if n_customers > 0 else 0.0
    )

    result = {
        "total_revenue": float(total_revenue),
        "n_customers": int(n_customers),
        "avg_revenue_per_customer": float(avg_revenue_per_customer),
    }

    if margin_col is not None and margin_col in df.columns:
        total_margin = df[margin_col].sum()
        result["total_margin"] = float(total_margin)

    return result


# -------------------------------------------------------------------
# 3. SIMULATION CLV PARAMÉTRIQUE (R, MARGE, REMISE)
# -------------------------------------------------------------------

def simulate_parametric_clv_scenario(
    base_margin: float,
    base_retention_rate: float,
    discount_rate: float,
    retention_uplift_pct: float = 0.0,
    margin_uplift_pct: float = 0.0,
    discount_pct: float = 0.0
) -> dict:
    """
    Simule l'impact d'un scénario sur la CLV paramétrique.

    Paramètres du scénario :
    - retention_uplift_pct : +r% sur la rétention (ex. 0.05 = +5 pts relatifs)
    - margin_uplift_pct    : +x% sur la marge (ex. 0.10 = +10 %)
    - discount_pct         : -y% de remise globale (affecte implicitement la marge)

    Hypothèse simplificatrice :
    - La remise se traduit par une baisse équivalente de la marge
      si on ne modifie pas le coût.

    Returns
    -------
    dict
        {
          "baseline_clv": ...,
          "scenario_clv": ...,
          "delta_clv": ...,
          "baseline_params": {...},
          "scenario_params": {...}
        }
    """
    # Baseline
    baseline_clv = clv_mod.clv_parametric(
        margin=base_margin,
        retention_rate=base_retention_rate,
        discount_rate=discount_rate
    )

    # Nouveau taux de rétention
    scenario_r = base_retention_rate * (1 + retention_uplift_pct)

    # Nouvelle marge :
    # marge initiale * (1 + uplift marge) * (1 - remise)
    scenario_margin = base_margin * (1 + margin_uplift_pct) * (1 - discount_pct)

    scenario_clv = clv_mod.clv_parametric(
        margin=scenario_margin,
        retention_rate=scenario_r,
        discount_rate=discount_rate
    )

    return {
        "baseline_clv": float(baseline_clv),
        "scenario_clv": float(scenario_clv),
        "delta_clv": float(scenario_clv - baseline_clv),
        "baseline_params": {
            "margin": base_margin,
            "retention_rate": base_retention_rate,
            "discount_rate": discount_rate,
        },
        "scenario_params": {
            "margin": scenario_margin,
            "retention_rate": scenario_r,
            "discount_rate": discount_rate,
            "retention_uplift_pct": retention_uplift_pct,
            "margin_uplift_pct": margin_uplift_pct,
            "discount_pct": discount_pct,
        },
    }


# -------------------------------------------------------------------
# 4. PIPELINE COMPLET DE SCÉNARIO SUR LES DONNÉES
# -------------------------------------------------------------------

def project_future_transactions_with_retention(
    df: pd.DataFrame,
    base_retention_rate: float,
    retention_uplift_pct: float,
    n_periods: int = 6,
    customer_col: str = "customer_id",
    date_col: str = "invoicedate",
    revenue_col: str = "revenue"
) -> pd.DataFrame:
    """
    Projette des transactions futures en fonction d'un taux de rétention amélioré.
    
    Logique CORRIGÉE :
    - Pour chaque période future, on calcule le % de clients qui restent actifs
    - On génère des transactions pour ces clients avec leur revenu moyen
    - La différence entre baseline et scénario vient du NOMBRE de clients actifs
    
    Exemple :
    - 1000 clients, retention baseline 60%, uplift +20% -> nouveau taux 72%
    - Période 1 : baseline = 600 clients, scénario = 720 clients (+120)
    - Période 2 : baseline = 360 clients, scénario = 518 clients (+158)
    
    Parameters
    ----------
    df : pd.DataFrame
        Données historiques
    base_retention_rate : float
        Taux de rétention baseline (ex. 0.65)
    retention_uplift_pct : float
        Amélioration relative (ex. 0.10 = +10%)
    n_periods : int
        Nombre de périodes futures à projeter
    customer_col : str
    date_col : str
    revenue_col : str
    
    Returns
    -------
    pd.DataFrame
        Transactions futures projetées avec le NOUVEAU taux de rétention
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    
    # Nouveau taux de rétention
    new_retention_rate = base_retention_rate * (1 + retention_uplift_pct)
    new_retention_rate = min(0.99, max(0.01, new_retention_rate))
    
    # Calculer le revenu moyen par client
    customer_stats = df.groupby(customer_col).agg({
        revenue_col: 'mean',
        date_col: 'max'
    }).reset_index()
    customer_stats.columns = [customer_col, 'avg_revenue', 'last_date']
    
    total_customers = len(customer_stats)
    max_date = df[date_col].max()
    
    # Générer les transactions futures
    future_transactions = []
    
    for period in range(1, n_periods + 1):
        # Nombre de clients actifs à cette période avec le NOUVEAU taux
        # Formule : N_actifs = N_total × retention_rate^period
        n_active_customers = int(total_customers * (new_retention_rate ** period))
        
        # Sélectionner les N premiers clients (déterministe)
        # On pourrait aussi faire un échantillonnage aléatoire avec seed fixe
        active_customers = customer_stats.head(n_active_customers)
        
        # Générer une transaction pour chaque client actif
        for _, customer in active_customers.iterrows():
            future_transactions.append({
                customer_col: customer[customer_col],
                date_col: max_date + pd.DateOffset(months=period),
                revenue_col: customer['avg_revenue'],  # Revenu COMPLET, pas pondéré
                'is_projected': True,
                'period': period,
                'retention_rate_used': new_retention_rate
            })
    
    if not future_transactions:
        return pd.DataFrame(columns=[customer_col, date_col, revenue_col, 'is_projected', 'period', 'retention_rate_used'])
    
    df_future = pd.DataFrame(future_transactions)
    return df_future


def prepare_scenario_dataframe(
    df_raw: pd.DataFrame,
    returns_policy: ReturnsPolicy = "include",
    drop_customers_na: bool = True,
    margin_rate: float = 0.3,
    discount_pct_global: float = 0.0,
    segment_discounts: Optional[Dict[str, float]] = None,
    segment_col: str = "segment_label",
    use_segment_discounts: bool = False,
    base_retention_rate: Optional[float] = None,
    retention_uplift_pct: float = 0.0,
    project_future: bool = True,
    n_future_periods: int = 6
) -> Tuple[pd.DataFrame, dict]:
    """
    Prépare un dataframe transactionnel enrichi pour un scénario
    donné, en tenant compte :

    - de la politique de retours (include/exclude/neutralize),
    - de l'exclusion des clients sans ID,
    - de l'application d'une marge (colonne 'margin'),
    - des remises globales ou par segment RFM,
    - de la projection de transactions futures basée sur la rétention.

    Cette fonction est conçue pour être appelée côté app Streamlit.

    Parameters
    ----------
    df_raw : pd.DataFrame
        Données brutes (après chargement)
    returns_policy : {"include", "exclude", "neutralize"}
    drop_customers_na : bool
    margin_rate : float
    discount_pct_global : float
        Remise globale (0.1 = -10%)
    segment_discounts : dict | None
        Remises par segment, ex. {"Champions": 0.05}
    segment_col : str
    use_segment_discounts : bool
        Si True, applique les remises par segment, sinon globale
    base_retention_rate : float | None
        Taux de rétention baseline (si None, pas de projection)
    retention_uplift_pct : float
        Amélioration relative de la rétention (ex. 0.10 = +10%)
    project_future : bool
        Si True, projette des transactions futures
    n_future_periods : int
        Nombre de périodes futures à projeter

    Returns
    -------
    df_prepared : pd.DataFrame
        Données prêtes avec colonne 'revenue_scenario' et 'margin_scenario'
    info : dict
        Quelques paramètres rappelés pour affichage
    """
    # Préparation de base (retours + clients)
    df_prepared = prep.prepare_base_dataframe(
        df_raw,
        drop_customers_na=drop_customers_na,
        returns_policy=returns_policy
    )

    # Projection de transactions futures si demandé
    if project_future and base_retention_rate is not None:
        df_future = project_future_transactions_with_retention(
            df_prepared,
            base_retention_rate=base_retention_rate,
            retention_uplift_pct=retention_uplift_pct,
            n_periods=n_future_periods,
            customer_col="customer_id",
            date_col="invoicedate",
            revenue_col="revenue"
        )
        
        # Marquer les transactions historiques
        df_prepared['is_projected'] = False
        
        # Combiner historique + projections
        if not df_future.empty:
            # S'assurer que df_future a les mêmes colonnes essentielles
            # On va ajouter les colonnes manquantes avec des valeurs par défaut
            for col in df_prepared.columns:
                if col not in df_future.columns and col != 'is_projected':
                    df_future[col] = None
            
            df_prepared = pd.concat([df_prepared, df_future], ignore_index=True)
    else:
        df_prepared['is_projected'] = False

    # Marge baseline
    df_prepared = compute_margin_column(
        df_prepared,
        revenue_col="revenue",
        margin_rate=margin_rate,
        new_col="margin_baseline"
    )

    # Application des remises
    if use_segment_discounts and segment_discounts is not None and segment_col in df_prepared.columns:
        df_prepared = apply_segment_discounts(
            df_prepared,
            segment_col=segment_col,
            revenue_col="revenue",
            segment_discounts=segment_discounts,
            default_discount=discount_pct_global,
            new_col="revenue_scenario"
        )
    else:
        df_prepared = apply_global_discount(
            df_prepared,
            discount_pct=discount_pct_global,
            revenue_col="revenue",
            new_col="revenue_scenario"
        )

    # Marge scénario (même taux de marge, mais sur revenu après remise)
    df_prepared = compute_margin_column(
        df_prepared,
        revenue_col="revenue_scenario",
        margin_rate=margin_rate,
        new_col="margin_scenario"
    )

    info = {
        "returns_policy": returns_policy,
        "margin_rate": margin_rate,
        "discount_pct_global": discount_pct_global,
        "use_segment_discounts": use_segment_discounts,
        "segment_discounts": segment_discounts or {},
        "base_retention_rate": base_retention_rate,
        "retention_uplift_pct": retention_uplift_pct,
        "n_projected_transactions": int(df_prepared['is_projected'].sum()) if 'is_projected' in df_prepared.columns else 0,
    }

    return df_prepared, info



def compare_baseline_scenario_kpis(
    df_prepared: pd.DataFrame,
    customer_col: str = "customer_id"
) -> dict:
    """
    Compare quelques KPIs entre baseline et scénario :

    - CA total baseline vs scénario
    - Marge totale baseline vs scénario
    - Δ absolu et relatif

    On suppose que df_prepared contient :
    - revenue (baseline)
    - margin_baseline
    - revenue_scenario
    - margin_scenario

    Returns
    -------
    dict
    """
    base_kpis = aggregate_kpis(
        df_prepared,
        revenue_col="revenue",
        margin_col="margin_baseline",
        customer_col=customer_col
    )
    scen_kpis = aggregate_kpis(
        df_prepared,
        revenue_col="revenue_scenario",
        margin_col="margin_scenario",
        customer_col=customer_col
    )

    delta_revenue = scen_kpis["total_revenue"] - base_kpis["total_revenue"]
    delta_margin = scen_kpis.get("total_margin", 0) - base_kpis.get("total_margin", 0)

    pct_revenue = (
        delta_revenue / base_kpis["total_revenue"]
        if base_kpis["total_revenue"] != 0 else 0.0
    )
    pct_margin = (
        delta_margin / base_kpis.get("total_margin", 1)
        if base_kpis.get("total_margin", 0) != 0 else 0.0
    )

    return {
        "baseline": base_kpis,
        "scenario": scen_kpis,
        "delta": {
            "revenue_abs": float(delta_revenue),
            "revenue_pct": float(pct_revenue),
            "margin_abs": float(delta_margin),
            "margin_pct": float(pct_margin),
        },
    }
