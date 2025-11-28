# app/pages/1_📊_KPIs.py

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from utils import visuals

st.set_page_config(page_title="KPIs - Online Retail II", layout="wide")

st.title("KPIs — Vue globale")

filters = visuals.render_global_sidebar()
df = visuals.get_prepared_data(
    returns_policy=filters["returns_policy"],
    drop_customers_na=filters["drop_customers_na"],
)
df = visuals.apply_filters(df, filters)

visuals.render_active_filters(filters)
st.markdown("---")

if df.empty:
    st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
    st.stop()

# ---------------- KPIs ----------------
daily_revenue = (
    df.groupby(df["invoicedate"].dt.date)["revenue"]
    .sum()
    .rename("revenue")
    .reset_index()
)
monthly_revenue = (
    df.groupby(df["invoicedate"].dt.to_period("M"))["revenue"]
    .sum()
    .reset_index()
)
monthly_revenue["invoicedate"] = monthly_revenue["invoicedate"].dt.to_timestamp()

total_revenue = df["revenue"].sum()
total_revenue_no_returns = df.loc[~df["is_return"], "revenue"].sum()
n_invoices = df["invoice"].nunique()
n_customers = df["customer_id"].nunique()
avg_basket = total_revenue / max(n_invoices, 1)

returns_share = df["is_return"].mean()
uk_share = (
    df["country"].value_counts(normalize=True).get("United Kingdom", 0.0)
)

col1, col2, col3, col4 = st.columns(4)
with col1:
    visuals.kpi_card(
        "CA total (filtré)",
        total_revenue,
        unit="€",
        help_text=(
            "Somme de `Quantity × Price` après filtres.\n"
            "Exemple : si trois factures de 100€, 200€ et -50€ (retour), "
            "alors CA total = 250€."
        ),
    )
with col2:
    visuals.kpi_card(
        "CA hors retours",
        total_revenue_no_returns,
        unit="€",
        help_text="Somme du CA uniquement sur les lignes avec `Quantity > 0`.",
    )
with col3:
    visuals.kpi_card(
        "Panier moyen par facture",
        avg_basket,
        unit="€",
        decimals=2,
        help_text=(
            "CA total / nb de factures.\n"
            "Exemple : 10 000€ de CA pour 100 factures => panier moyen = 100€."
        ),
    )
with col4:
    visuals.kpi_card(
        "Part de lignes de retour",
        returns_share,
        unit="",
        decimals=2,
        help_text=(
            "Nombre de lignes avec `Quantity < 0` / nombre total de lignes.\n"
            "Exemple : 20 lignes de retour sur 200 lignes => 10%."
        ),
    )


st.markdown("---")

# -------------- Graphique CA quotidien --------------
st.subheader("Évolution du CA quotidien")
visuals.line_chart(
    daily_revenue,
    x="invoicedate",
    y="revenue",
    title="CA quotidien",
    xaxis_title="Date",
    yaxis_title="CA",
)

st.info(
    "Chaque point correspond au CA total d'une journée, retours inclus ou non "
    "selon la politique choisie dans la sidebar."
)

# -------------- Graphique CA mensuel --------------
st.subheader("CA mensuel (fenêtre filtrée)")
visuals.line_chart(
    monthly_revenue,
    x="invoicedate",
    y="revenue",
    title="CA mensuel",
    xaxis_title="Mois",
    yaxis_title="CA",
)

# -------------- Répartition pays --------------
st.subheader("Répartition du CA par pays")

country_revenue = (
    df.groupby("country")["revenue"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)
top_n = st.slider("Nombre de pays à afficher", 3, 20, 10)

visuals.bar_chart(
    country_revenue.head(top_n),
    x="country",
    y="revenue",
    title=f"Top {top_n} pays par CA",
)
st.caption(
    "Exemple d'interprétation : si le Royaume-Uni représente 80% du CA, "
    "les analyses cohortes/CLV peuvent d'abord se concentrer sur ce marché."
)

# -------------- Info accessibilité --------------
st.markdown("---")
st.caption(
    "Les couleurs et tailles de police ont été choisies pour conserver un contraste suffisant. "
    "Les valeurs sont également indiquées dans les infobulles des graphiques."
)
