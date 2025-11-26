# app/pages/4_🎛️_Scenarios_CLV.py

import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from utils import (
    visuals,
    cohorts,
    rfm as rfm_mod,
    clv as clv_mod,
    simulation as sim_mod,
)

st.set_page_config(page_title="🎛️ Scénarios CLV - Online Retail II", layout="wide")

st.title("🎛️ Simulation de scénarios CLV")

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
    st.warning("Aucune donnée disponible pour la simulation CLV avec ces filtres.")
    st.stop()

# ---------------- Baseline RFM + segments (pour remises par segment) ---------------
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

df = df.merge(
    rfm[["customer_id", "segment_label"]],
    on="customer_id",
    how="left",
)

# ---------------- Estimation de la rétention moyenne baseline --------------------
df_cohort = cohorts.assign_cohort(df)
retention_table, _ = cohorts.build_retention_table(df_cohort)

# On définit un r moyen : moyenne de tous les âges >= 1 (on ignore M+0)
if retention_table.shape[1] > 1:
    baseline_r = retention_table.iloc[:, 1:].stack().mean()
else:
    baseline_r = 0.5  # fallback

st.subheader("⚙️ Paramètres de base CLV paramétrique")

col_l, col_r = st.columns(2)
with col_l:
    base_margin = st.number_input(
        "Marge moyenne par période (€/client)",
        min_value=0.0,
        value=30.0,
        step=5.0,
        help=(
            "Exemple : si un client moyen génère 100€ de CA par mois avec 30% de marge, "
            "la marge mensuelle moyenne est 30€."
        ),
    )
    discount_rate = st.number_input(
        "Taux d’actualisation par période",
        min_value=0.0,
        max_value=1.0,
        value=0.10,
        step=0.01,
        help=(
            "Taux de décote appliqué aux flux futurs.\n"
            "Exemple : 0.10 signifie qu’un euro dans un mois vaut 0.90€ aujourd’hui."
        ),
    )
with col_r:
    st.metric(
        "Rétention moyenne empirique (baseline)",
        f"{baseline_r:.1%}",
    )
    st.caption(
        "Estimée à partir de la heatmap de rétention (moyenne des taux pour M+1, M+2, ...)."
    )

st.markdown("---")
st.subheader("🎚️ Paramètres du scénario")

col1, col2, col3 = st.columns(3)
with col1:
    retention_uplift_pct = st.slider(
        "Amélioration de la rétention (r)",
        min_value=-0.5,
        max_value=0.5,
        value=0.05,
        step=0.01,
        format="%.2f",
        help="Exemple : 0.05 signifie +5% relatif sur le taux de rétention moyen.",
    )
with col2:
    margin_uplift_pct = st.slider(
        "Augmentation de la marge",
        min_value=-0.5,
        max_value=0.5,
        value=0.10,
        step=0.01,
        format="%.2f",
        help="Exemple : 0.10 signifie +10% sur la marge moyenne par client.",
    )
with col3:
    discount_pct_global = st.slider(
        "Remise globale sur le CA",
        min_value=0.0,
        max_value=0.8,
        value=0.0,
        step=0.05,
        format="%.2f",
        help="Exemple : 0.20 signifie une remise de -20% sur tous les montants.",
    )

st.markdown("#### Mode d’application des remises")
mode_discounts = st.radio(
    "Choix du mode",
    options=["global", "segment"],
    format_func=lambda x: "Remise globale" if x == "global" else "Remises par segment RFM",
)

segment_discounts = None
if mode_discounts == "segment":
    st.markdown("##### Paramétrage des remises par segment")
    segment_discounts = {}
    for seg in sorted(rfm["segment_label"].dropna().unique()):
        segment_discounts[seg] = st.slider(
            f"Remise pour segment '{seg}'",
            min_value=0.0,
            max_value=0.8,
            value=0.0,
            step=0.05,
            format="%.2f",
            key=f"discount_{seg}",
        )
    st.caption(
        "Exemple : appliquer 5% de remise sur les 'Champions' et 20% sur les segments 'À risque'."
    )

st.markdown("---")
if st.button("🚀 Lancer la simulation"):
    # ---------------- CLV paramétrique ----------------
    clv_result = sim_mod.simulate_parametric_clv_scenario(
        base_margin=base_margin,
        base_retention_rate=baseline_r,
        discount_rate=discount_rate,
        retention_uplift_pct=retention_uplift_pct,
        margin_uplift_pct=margin_uplift_pct,
        discount_pct=discount_pct_global if mode_discounts == "global" else 0.0,
    )

    baseline_clv = clv_result["baseline_clv"]
    scenario_clv = clv_result["scenario_clv"]
    delta_clv = clv_result["delta_clv"]

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        visuals.kpi_card(
            "CLV paramétrique — baseline",
            baseline_clv,
            unit="€",
            decimals=2,
            help_text=(
                "Calculée avec la formule CLV = (marge × r) / (1 + d − r) "
                "et les paramètres de base."
            ),
        )
    with col_b:
        visuals.kpi_card(
            "CLV paramétrique — scénario",
            scenario_clv,
            unit="€",
            decimals=2,
        )
    with col_c:
        visuals.kpi_card(
            "Δ CLV (scénario - baseline)",
            delta_clv,
            unit="€",
            decimals=2,
        )

    # ---------------- Préparation scénario sur données réelles ----------------
    df_scenario, info = sim_mod.prepare_scenario_dataframe(
        df_raw=visuals.load_raw_data(),  # on repart du brut
        returns_policy=filters["returns_policy"],
        drop_customers_na=True,
        margin_rate=base_margin / 100.0 if base_margin > 0 else 0.3,  # simplification
        discount_pct_global=discount_pct_global,
        segment_discounts=segment_discounts,
        segment_col="segment_label",
        use_segment_discounts=(mode_discounts == "segment"),
    )

    # Réappliquer filtres pour cohérence
    df_scenario = visuals.apply_filters(df_scenario, filters)

    kpi_compare = sim_mod.compare_baseline_scenario_kpis(df_scenario)

    st.markdown("---")
    st.subheader("📊 Comparaison CA & marge — baseline vs scénario")

    df_kpis = pd.DataFrame(
        [
            {
                "version": "Baseline",
                "CA": kpi_compare["baseline"]["total_revenue"],
                "Marge": kpi_compare["baseline"].get("total_margin", 0),
            },
            {
                "version": "Scénario",
                "CA": kpi_compare["scenario"]["total_revenue"],
                "Marge": kpi_compare["scenario"].get("total_margin", 0),
            },
        ]
    )

    fig_kpi = px.bar(
        df_kpis.melt(id_vars="version", value_vars=["CA", "Marge"], var_name="KPI", value_name="Valeur"),
        x="KPI",
        y="Valeur",
        color="version",
        barmode="group",
        title="Baseline vs scénario — CA & marge",
    )
    st.plotly_chart(fig_kpi, use_container_width=True)
    visuals.download_fig_button(fig_kpi, "baseline_vs_scenario_CA_marge.png")

    st.caption(
        "Les deltas affichent l'impact combiné de la politique de retours, des remises et "
        "du changement de marge sur le CA et la marge totaux."
    )

    # ---------------- Courbe de sensibilité CLV(r) ----------------
    st.markdown("---")
    st.subheader("📈 Courbe de sensibilité CLV(r)")

    sens_df = clv_mod.clv_sensitivity_curve(
        margin=base_margin,
        discount_rate=discount_rate,
        r_min=max(0.05, baseline_r / 2),
        r_max=min(0.99, baseline_r * 1.5),
        n_points=50,
    )

    fig_sens = px.line(
        sens_df,
        x="retention_rate",
        y="clv",
        title="CLV en fonction du taux de rétention r",
    )
    fig_sens.add_vline(
        x=baseline_r,
        line_dash="dash",
        line_color="red",
        annotation_text="Baseline r",
    )

    st.plotly_chart(fig_sens, use_container_width=True)
    visuals.download_fig_button(fig_sens, "sensibilite_clv_r.png")

    st.info(
        "Lecture : si le taux de rétention passe de 70% à 80%, la CLV peut augmenter très fortement. "
        "Cette courbe aide à évaluer le ROI attendu d'actions de fidélisation."
    )
else:
    st.info("Configure les paramètres puis clique sur **🚀 Lancer la simulation**.")
