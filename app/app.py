# app/app.py

import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from utils import visuals

st.set_page_config(
    page_title="Online Retail II – Marketing Decision App",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* Légère amélioration globale : fond, police, etc. */
    .main > div {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Online Retail II — Marketing Decision App")
st.caption(
    "Cohortes d’acquisition · Segmentation RFM · CLV · Simulation de scénarios."
)

# Sidebar filtres globaux (partage logique avec les pages)
filters = visuals.render_global_sidebar()
df = visuals.get_prepared_data(
    returns_policy=filters["returns_policy"],
    drop_customers_na=filters["drop_customers_na"],
)
df = visuals.apply_filters(df, filters)

st.markdown("### Vue d’ensemble")

visuals.render_active_filters(filters)

if df.empty:
    st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
else:
    # KPIs globaux simples
    total_revenue = df["revenue"].sum()
    total_invoices = df["invoice"].nunique()
    n_customers = df["customer_id"].nunique()
    returns_rate = df["is_return"].mean() if "is_return" in df.columns else 0.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        visuals.kpi_card(
            "CA total (filtré)",
            total_revenue,
            unit="€",
            help_text="Somme de `Quantity × Price` après application de tous les filtres.",
        )
    with col2:
        visuals.kpi_card(
            "Nombre de factures",
            total_invoices,
            help_text="Nombre de valeurs uniques dans `Invoice` après filtres.",
        )
    with col3:
        visuals.kpi_card(
            "Clients uniques",
            n_customers,
            help_text=(
                "Nombre de `Customer ID` distincts. "
                "Exemple : si 3 factures appartiennent au même client, on compte 1."
            ),
        )
    with col4:
        visuals.kpi_card(
            "Part de lignes de retour",
            returns_rate,
            unit="",
            decimals=2,
            help_text=(
                "Proportion de lignes où `Quantity < 0`. "
                "Exemple : si 10 lignes sur 100 sont des retours, le taux est 10%."
            ),
        )

    st.markdown("---")
    
    st.markdown("### Origine des commandes")
    visuals.map_chart(df, title="Répartition mondiale du Chiffre d'Affaires")

    st.markdown("---")
    st.markdown("### Navigation")

    st.markdown(
        """
        - **KPIs** : indicateurs globaux, dynamique de CA, répartition pays.
        - **Cohortes** : rétention M+1, M+2…, valeur cumulée par âge de cohorte.
        - **Segments RFM** : Champions, Loyaux, À risque, Perdus…
        - **Scénarios CLV** : simulations sur rétention, marge, remises.
        - **Export** : extractions CSV des tables clés.
        """
    )

    st.info(
        "Tous les filtres applicables (dates, pays, retours, clients anonymes) "
        "sont contrôlés via la barre latérale et s’appliquent à l’ensemble des pages."
    )
