# app/pages/3_💎_Segments_RFM.py

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from utils import visuals, rfm as rfm_mod

st.set_page_config(page_title="💎 RFM - Online Retail II", layout="wide")

st.title("💎 Segmentation RFM & segments marketing")

filters = visuals.render_global_sidebar()
df = visuals.get_prepared_data(
    returns_policy=filters["returns_policy"],
    drop_customers_na=True,
)
df = visuals.apply_filters(df, filters)
df = df[df["customer_id"].notna()].copy()

visuals.render_active_filters(filters)
st.markdown("---")

if df.empty:
    st.warning("Aucune donnée disponible pour la segmentation RFM avec ces filtres.")
    st.stop()

# --------- RFM ---------
st.subheader("📐 Calcul RFM")

snapshot_date = df["invoicedate"].max() + pd.Timedelta(days=1)
rfm = rfm_mod.compute_rfm(
    df,
    snapshot_date=snapshot_date,
    customer_col="customer_id",
    date_col="invoicedate",
    invoice_col="invoice",
    revenue_col="revenue",
)
rfm = rfm_mod.score_rfm(rfm)
rfm = rfm_mod.label_rfm_segments(rfm)

st.caption(
    f"Date de référence (snapshot) pour la recency : **{snapshot_date.date()}**. "
    "Recency = nombre de jours depuis la dernière transaction."
)

col1, col2, col3 = st.columns(3)
with col1:
    visuals.kpi_card(
        "Clients uniques",
        rfm["customer_id"].nunique(),
        help_text="Nombre de lignes distinctes dans la table RFM.",
    )
with col2:
    visuals.kpi_card(
        "Recency médiane (jours)",
        rfm["recency"].median(),
        decimals=0,
        help_text=(
            "Exemple : recency = 10 signifie que la dernière transaction du client "
            "date d'il y a 10 jours par rapport au snapshot."
        ),
    )
with col3:
    visuals.kpi_card(
        "Monetary médian",
        rfm["monetary"].median(),
        unit="€",
        decimals=2,
        help_text="CA médian par client sur la période filtrée.",
    )

# --------- Distribution segments ---------
st.markdown("---")
st.subheader("🏷️ Répartition des segments")

segment_summary = rfm_mod.summarize_rfm_segments(rfm, margin_rate=None)

visuals.bar_chart(
    segment_summary,
    x="segment_label",
    y="n_clients",
    title="Nombre de clients par segment RFM",
)

visuals.bar_chart(
    segment_summary,
    x="segment_label",
    y="ca_total",
    title="CA total par segment RFM",
)

st.info(
    "Exemple : un segment 'Champions' avec 50 clients et 50 000€ de CA signifie "
    "un CA moyen de 1 000€ par client dans ce segment."
)

# --------- Scatter Frequency vs Monetary ---------
st.markdown("---")
st.subheader("📊 Nuage de points Frequency vs Monetary")

fig_scatter = px.scatter(
    rfm,
    x="frequency",
    y="monetary",
    color="segment_label",
    hover_data=["customer_id", "recency"],
    title="Frequency vs Monetary par segment",
)
fig_scatter.update_layout(margin=dict(l=10, r=10, t=50, b=10))
st.plotly_chart(fig_scatter, use_container_width=True)
visuals.download_fig_button(fig_scatter, "rfm_scatter_frequency_monetary.png")

st.caption(
    "Les clients en haut à droite (forte fréquence, fort monetary) sont typiquement "
    "les 'Champions' / clients stratégiques."
)

# --------- Table détaillée ---------
st.markdown("---")
st.subheader("📋 Table RFM détaillée")

st.dataframe(
    rfm.sort_values("monetary", ascending=False).head(200),
    use_container_width=True,
)
st.caption("Les 200 clients les plus contributifs par CA.")
