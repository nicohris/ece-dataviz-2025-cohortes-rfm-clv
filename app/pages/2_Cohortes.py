# app/pages/2_🔥_Cohortes.py

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from utils import visuals, cohorts

st.set_page_config(page_title="Cohortes - Online Retail II", layout="wide")

st.title("Cohortes d’acquisition & rétention")

filters = visuals.render_global_sidebar()
df = visuals.get_prepared_data(
    returns_policy=filters["returns_policy"],
    drop_customers_na=True,  # cohorte : on se concentre sur clients identifiés
)
df = visuals.apply_filters(df, filters)
df = df[df["customer_id"].notna()].copy()

visuals.render_active_filters(filters)
st.markdown("---")

if df.empty:
    st.warning("Aucune donnée disponible pour les cohortes avec ces filtres.")
    st.stop()

# ---------------- Construction des cohortes ----------------
df_cohort = cohorts.assign_cohort(df)

retention_table, counts_table = cohorts.build_retention_table(df_cohort)
revenue_table, revenue_cum_table = cohorts.build_revenue_tables(df_cohort)

st.subheader("Heatmap de rétention (premier focus)")
st.caption(
    "Les valeurs représentent la part de clients d'une cohorte encore actifs à un âge donné "
    "(M+0, M+1, M+2, ...)."
)

retention_table = retention_table.copy()
retention_table.index = retention_table.index.astype(str)
retention_table.columns = retention_table.columns.astype(str)

fig_ret = px.imshow(
    retention_table,
    labels=dict(x="Âge de cohorte (mois)", y="Cohorte (AAAA-MM)", color="Rétention"),
    color_continuous_scale="Blues",
    aspect="auto",
)
fig_ret.update_layout(margin=dict(l=10, r=10, t=40, b=10), title="Heatmap de rétention par cohorte")

st.plotly_chart(fig_ret, use_container_width=True)
visuals.download_fig_button(fig_ret, filename="heatmap_cohortes_retention.png")

st.info(
    "Exemple : si une cohorte a 100 clients à M+0 et 40 clients encore actifs à M+3, "
    "le taux de rétention à M+3 est 40%."
)

# ---------------- Densité du CA par âge de cohorte ----------------
st.markdown("---")
st.subheader("Densité du CA par âge de cohorte")

# On normalise par le CA total de la cohorte
rev_share = revenue_table.div(revenue_table.sum(axis=1), axis=0)

rev_share = rev_share.copy()
rev_share.index = rev_share.index.astype(str)
rev_share.columns = rev_share.columns.astype(str)

fig_rev_share = px.imshow(
    rev_share,
    labels=dict(x="Âge de cohorte (mois)", y="Cohorte (AAAA-MM)", color="Part du CA"),
    color_continuous_scale="Greens",
    aspect="auto",
)
fig_rev_share.update_layout(
    title="Part du CA par âge de cohorte (par cohorte)",
    margin=dict(l=10, r=10, t=40, b=10),
)
st.plotly_chart(fig_rev_share, use_container_width=True)
visuals.download_fig_button(fig_rev_share, filename="cohort_revenue_share.png")

st.caption(
    "Lecture : pour chaque cohorte (ligne), les valeurs indiquent la répartition du CA "
    "entre les différents âges (la somme par ligne vaut 100%)."
)

# ---------------- Valeur cumulée par âge ----------------
st.markdown("---")
st.subheader("Valeur cumulée par âge de cohorte")

avg_rev_per_age = cohorts.compute_avg_revenue_per_age(revenue_table)
avg_rev_cum = avg_rev_per_age.cumsum()

df_val_cum = pd.DataFrame(
    {"age": avg_rev_per_age.index, "revenu_moyen": avg_rev_per_age.values, "revenu_cumule": avg_rev_cum.values}
)

col_l, col_r = st.columns(2)
with col_l:
    st.markdown("##### Revenu moyen par âge (tous cohortes confondues)")
    visuals.line_chart(
        df_val_cum,
        x="age",
        y="revenu_moyen",
        title="Revenu moyen par âge de cohorte",
        xaxis_title="Âge (mois depuis acquisition)",
        yaxis_title="Revenu moyen par client",
    )

with col_r:
    st.markdown("##### Revenu cumulatif moyen par âge")
    visuals.line_chart(
        df_val_cum,
        x="age",
        y="revenu_cumule",
        title="Revenu cumulatif moyen par âge",
        xaxis_title="Âge (mois depuis acquisition)",
        yaxis_title="Revenu cumulé moyen par client",
    )

st.info(
    "Exemple : si aux âges 0, 1 et 2 mois le revenu moyen par client est [10, 8, 4], "
    "la courbe cumulée affiche [10, 18, 22]."
)

# ---------------- Focus sur une cohorte ----------------
st.markdown("---")
st.subheader("Focus sur une cohorte spécifique")

cohort_options = retention_table.index.tolist()
selected_cohort_str = st.selectbox("Choisir une cohorte (AAAA-MM)", cohort_options)

selected_period = selected_cohort_str

retention_line = retention_table.loc[selected_period].reset_index()
retention_line.columns = ["age", "retention"]

revenue_line = revenue_table.loc[selected_period].reset_index()
revenue_line.columns = ["age", "revenue"]


col1, col2 = st.columns(2)
with col1:
    visuals.line_chart(
        retention_line,
        x="age",
        y="retention",
        title=f"Rétention de la cohorte {selected_cohort_str}",
        xaxis_title="Âge (mois)",
        yaxis_title="Taux de rétention",
    )
with col2:
    visuals.line_chart(
        revenue_line,
        x="age",
        y="revenue",
        title=f"CA de la cohorte {selected_cohort_str}",
        xaxis_title="Âge (mois)",
        yaxis_title="CA",
    )
