"""
rfm.py
---------------------------------
Fonctions pour calculer les indicateurs RFM et les segments marketing.

- compute_rfm() : calcule Recency, Frequency, Monetary par client
- score_rfm() : scores 1–5 (quantiles) pour R, F, M
- label_rfm_segments() : labels marketing (Champions, Loyal, Potentiels, À risque, Perdus)
- summarize_rfm_segments() : tableau de synthèse par segment

Rappels :
- Recency : nb de jours depuis la dernière transaction (plus petit = mieux)
- Frequency : nb de factures
- Monetary : CA total

Les règles de scoring et de labellisation peuvent être ajustées
selon la stratégie marketing.
"""

from __future__ import annotations

from typing import Optional, Dict

import pandas as pd
import numpy as np


# -------------------------------------------------------------------
# 1. CALCUL RFM
# -------------------------------------------------------------------

def compute_rfm(
    df: pd.DataFrame,
    snapshot_date: Optional[pd.Timestamp] = None,
    customer_col: str = "customer_id",
    date_col: str = "invoicedate",
    invoice_col: str = "invoice",
    revenue_col: str = "revenue"
) -> pd.DataFrame:
    """
    Calcule les indicateurs RFM par client.

    Parameters
    ----------
    df : pd.DataFrame
        Données transactionnelles préparées
    snapshot_date : pd.Timestamp | None
        Date de référence pour le calcul de la recency.
        Si None, utilise max(invoicedate) + 1 jour.
    customer_col : str
    date_col : str
    invoice_col : str
    revenue_col : str

    Returns
    -------
    rfm : pd.DataFrame
        Colonnes : customer_id, recency, frequency, monetary

    Exemple numérique
    -----------------
    - Client A :
        * dernière transaction le 2021-01-10
        * snapshot_date = 2021-01-15
        -> recency = 5 jours
        * 3 factures uniques -> frequency = 3
        * CA total = 250 -> monetary = 250
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    if snapshot_date is None:
        snapshot_date = df[date_col].max() + pd.Timedelta(days=1)

    grouped = (
        df.groupby(customer_col)
        .agg(
            recency=(date_col, lambda x: (snapshot_date - x.max()).days),
            frequency=(invoice_col, "nunique"),
            monetary=(revenue_col, "sum"),
        )
        .reset_index()
    )

    return grouped


# -------------------------------------------------------------------
# 2. SCORING RFM
# -------------------------------------------------------------------

def _score_series_quantiles(
    s: pd.Series,
    n_bins: int = 5,
    reverse: bool = False
) -> pd.Series:
    """
    Transforme une série en scores 1..n_bins selon les quantiles.

    reverse=False : valeurs élevées -> score élevé (1..n)
    reverse=True  : valeurs élevées -> score faible (n..1)
                    (utile pour Recency : petit nb de jours = meilleur score)
    """
    # qcut peut échouer si beaucoup de doublons; on gère avec rank
    try:
        bins = pd.qcut(s.rank(method="first"), n_bins, labels=False) + 1
    except ValueError:
        # fallback : use rank only
        bins = pd.qcut(
            s.rank(method="average"),
            n_bins,
            duplicates="drop",
            labels=False
        ) + 1

    if reverse:
        return (n_bins + 1) - bins

    return bins


def score_rfm(
    rfm: pd.DataFrame,
    recency_col: str = "recency",
    frequency_col: str = "frequency",
    monetary_col: str = "monetary",
    prefix: str = "RFM_"
) -> pd.DataFrame:
    """
    Ajoute des scores 1–5 pour Recency, Frequency, Monetary.

    - Recency : plus petit = mieux -> reverse=True
    - Frequency : plus grand = mieux
    - Monetary : plus grand = mieux

    Ajoute les colonnes :
    - f"{prefix}R"
    - f"{prefix}F"
    - f"{prefix}M"
    - f"{prefix}score" (concaténation en chaîne, ex. "555", "312")

    Returns
    -------
    pd.DataFrame
    """
    rfm = rfm.copy()

    rfm[f"{prefix}R"] = _score_series_quantiles(
        rfm[recency_col],
        n_bins=5,
        reverse=True
    )
    rfm[f"{prefix}F"] = _score_series_quantiles(
        rfm[frequency_col],
        n_bins=5,
        reverse=False
    )
    rfm[f"{prefix}M"] = _score_series_quantiles(
        rfm[monetary_col],
        n_bins=5,
        reverse=False
    )

    # Score concaténé, utile pour certaines logiques de segmentation
    rfm[f"{prefix}score"] = (
        rfm[f"{prefix}R"].astype(str)
        + rfm[f"{prefix}F"].astype(str)
        + rfm[f"{prefix}M"].astype(str)
    )

    return rfm


# -------------------------------------------------------------------
# 3. LABELS SEGMENTS
# -------------------------------------------------------------------

def _default_segment_mapping() -> Dict[str, str]:
    """
    Mapping simple RFM_score -> segment marketing.

    Cette version s'appuie principalement sur R et F.
    On utilise des patterns sur les deux premiers caractères (R et F).

    Exemples :
    - "55x", "54x" : Champions
    - "45x", "44x", "35x" : Loyal
    - "5[1-3]x", "4[1-2]x" : Potentiels
    - "3[1-3]x", "2[2-4]x" : À risque
    - "1xx", "2[0-1]x" : Perdus
    """
    return {
        "Champions":       ["55", "54", "45"],
        "Loyal":           ["44", "53", "35", "43"],
        "Potentiels":      ["51", "52", "41", "42"],
        "À risque":        ["33", "32", "23", "24"],
        "Perdus":          ["11", "12", "13", "21", "22"],
    }


def label_rfm_segments(
    rfm: pd.DataFrame,
    score_col: str = "RFM_score",
    segment_col: str = "segment_label",
    mapping: Optional[Dict[str, list[str]]] = None
) -> pd.DataFrame:
    """
    Assigne un label de segment marketing à chaque client
    à partir de son score RFM concaténé.

    Parameters
    ----------
    rfm : pd.DataFrame
        Table RFM déjà scorée avec une colonne score (ex. "RFM_score").
    score_col : str
        Colonne contenant la chaîne de score, ex. "555".
    segment_col : str
        Nom de la colonne de segments à créer.
    mapping : dict | None
        Dictionnaire {nom_segment: [préfixes_RFe]}

    Returns
    -------
    pd.DataFrame
        rfm enrichi avec segment_col
    """
    rfm = rfm.copy()

    if mapping is None:
        mapping = _default_segment_mapping()

    def _assign_segment(score: str) -> str:
        if not isinstance(score, str) or len(score) < 2:
            return "Autres"

        rf_prefix = score[:2]  # on regarde R et F

        for segment_name, prefixes in mapping.items():
            if rf_prefix in prefixes:
                return segment_name

        return "Autres"

    rfm[segment_col] = rfm[score_col].apply(_assign_segment)
    return rfm


# -------------------------------------------------------------------
# 4. SYNTHÈSE PAR SEGMENT
# -------------------------------------------------------------------

def summarize_rfm_segments(
    rfm: pd.DataFrame,
    segment_col: str = "segment_label",
    monetary_col: str = "monetary",
    margin_rate: Optional[float] = None
) -> pd.DataFrame:
    """
    Produit une table de synthèse RFM par segment.

    Colonnes de sortie :
    - segment_label
    - n_clients
    - ca_total
    - panier_moyen (CA moyen par client)
    - marge (si margin_rate est fourni)

    Exemple numérique
    -----------------
    Si un segment contient :
    - 100 clients
    - CA total = 10 000
    - margin_rate = 0.3
    Alors :
    - panier_moyen = 10 000 / 100 = 100
    - marge = 10 000 * 0.3 = 3 000
    """
    rfm = rfm.copy()

    agg = (
        rfm.groupby(segment_col)[monetary_col]
        .agg(
            ca_total="sum",
            n_clients="count"
        )
        .reset_index()
    )

    agg["panier_moyen"] = agg["ca_total"] / agg["n_clients"]

    if margin_rate is not None:
        agg["marge"] = agg["ca_total"] * margin_rate

    # Ordre des colonnes
    cols = [segment_col, "n_clients", "ca_total", "panier_moyen"]
    if margin_rate is not None:
        cols.append("marge")

    return agg[cols]
