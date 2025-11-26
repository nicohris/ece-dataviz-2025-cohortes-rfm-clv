"""
clv.py
---------------------------------
Fonctions de calcul de CLV :

1) Approche empirique via cohortes :
   - clv_empirical_from_avg_revenue()

2) Approche paramétrique (formule fermée) :
   - clv_parametric()

La CLV empirique s'appuie sur la somme du revenu moyen
par âge de cohorte.

La CLV paramétrique utilise la formule :
    CLV = (marge * r) / (1 + d - r)

où :
- marge : marge moyenne par période (ex. par mois)
- r : taux de rétention par période (0..1)
- d : taux d'actualisation par période (0..1)
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import numpy as np


# -------------------------------------------------------------------
# 1. CLV EMPIRIQUE (COHORTES)
# -------------------------------------------------------------------

def clv_empirical_from_avg_revenue(
    avg_revenue_per_age: pd.Series,
    margin_rate: Optional[float] = None,
    discount_rate: float = 0.0
) -> float:
    """
    Calcule une CLV empirique à partir du revenu moyen
    par âge de cohorte.

    Idée :
    - avg_revenue_per_age[i] = revenu moyen au mois i
    - On applique un taux de marge éventuel et un discounting.

    Formule par âge t :
        contribution_t = revenu_t * (1 - remise) * marge_rate * 1 / (1 + discount_rate)^t

    Dans cette fonction, on suppose :
        revenu_t = avg_revenue_per_age[t]
        marge_t  = revenu_t * margin_rate (si fourni)
        actualisation : 1 / (1 + discount_rate)^t

    Parameters
    ----------
    avg_revenue_per_age : pd.Series
        index = âge de cohorte (0, 1, ..., T),
        values = revenu moyen par client à cet âge.
    margin_rate : float | None
        Si fourni, applique un taux de marge constant sur le revenu.
    discount_rate : float
        Taux d'actualisation par période (ex. mensuel).

    Returns
    -------
    float
        CLV empirique estimée.

    Exemple simple
    --------------
    - Revenu moyen par âge : [10, 8, 6]
    - margin_rate = 0.3
    - discount_rate = 0

    CLV = (10 + 8 + 6) * 0.3 = 7.2
    """
    ages = avg_revenue_per_age.index.to_numpy()
    revenues = avg_revenue_per_age.to_numpy().astype(float)

    # Marge
    if margin_rate is not None:
        margin = revenues * margin_rate
    else:
        margin = revenues

    # Actualisation
    discount_factors = 1 / ((1 + discount_rate) ** ages)

    clv = float(np.sum(margin * discount_factors))
    return clv


# -------------------------------------------------------------------
# 2. CLV PARAMÉTRIQUE
# -------------------------------------------------------------------

def clv_parametric(
    margin: float,
    retention_rate: float,
    discount_rate: float
) -> float:
    """
    Calcule la CLV paramétrique avec la formule fermée :

        CLV = (marge × r) / (1 + d − r)

    où :
    - marge : marge moyenne par période (ex. par mois) par client
    - r : taux de rétention moyen par période (0..1)
    - d : taux d'actualisation par période (0..1)

    Conditions :
    - 0 <= r < 1
    - d >= 0
    - 1 + d - r > 0

    Exemple numérique
    -----------------
    - marge = 30 € / mois
    - r = 0.8
    - d = 0.1

    CLV = (30 * 0.8) / (1 + 0.1 - 0.8)
        = 24 / 0.3
        = 80 €

    Parameters
    ----------
    margin : float
    retention_rate : float
    discount_rate : float

    Returns
    -------
    float
    """
    if not (0 <= retention_rate < 1):
        raise ValueError("retention_rate doit être dans [0, 1).")

    if discount_rate < 0:
        raise ValueError("discount_rate doit être >= 0.")

    denominator = 1 + discount_rate - retention_rate
    if denominator <= 0:
        raise ValueError("1 + discount_rate - retention_rate doit être > 0.")

    clv = (margin * retention_rate) / denominator
    return float(clv)


def clv_sensitivity_curve(
    margin: float,
    discount_rate: float,
    r_min: float = 0.1,
    r_max: float = 0.99,
    n_points: int = 50
) -> pd.DataFrame:
    """
    Génère une courbe de sensibilité CLV(r) pour différents
    niveaux de rétention.

    Utile pour l'interface de simulation :
    -> courbe CLV en fonction de r, pour un couple (marge, d) donné.

    Parameters
    ----------
    margin : float
    discount_rate : float
    r_min : float
    r_max : float
    n_points : int

    Returns
    -------
    pd.DataFrame
        colonnes : ['retention_rate', 'clv']
    """
    r_values = np.linspace(r_min, r_max, n_points)
    clv_values = []

    for r in r_values:
        try:
            clv_val = clv_parametric(margin=margin,
                                     retention_rate=r,
                                     discount_rate=discount_rate)
        except ValueError:
            clv_val = np.nan
        clv_values.append(clv_val)

    return pd.DataFrame(
        {"retention_rate": r_values, "clv": clv_values}
    )
