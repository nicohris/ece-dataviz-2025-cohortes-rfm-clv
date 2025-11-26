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

def prepare_scenario_dataframe(
    df_raw: pd.DataFrame,
    returns_policy: ReturnsPolicy = "include",
    drop_customers_na: bool = True,
    margin_rate: float = 0.3,
    discount_pct_global: float = 0.0,
    segment_discounts: Optional[Dict[str, float]] = None,
    segment_col: str = "segment_label",
    use_segment_discounts: bool = False
) -> Tuple[pd.DataFrame, dict]:
    """
    Prépare un dataframe transactionnel enrichi pour un scénario
    donné, en tenant compte :

    - de la politique de retours (include/exclude/neutralize),
    - de l'exclusion des clients sans ID,
    - de l'application d'une marge (colonne 'margin'),
    - des remises globales ou par segment RFM.

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
