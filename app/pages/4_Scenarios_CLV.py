# app/pages/4_🎛️_Scenarios_CLV.py

"""
Page Scénarios CLV - Simulation d'impact business
==================================================
Permet de tester des scénarios (ex. +5% de rétention, -10% de remise)
et d'évaluer l'impact sur la CLV, le CA et la marge.

Objectifs :
- Quantifier Δ CLV / Δ CA / Δ Marge pour aider à décider
- Comparer baseline (situation actuelle) vs scénario (avec modifications)
- Afficher les sensibilités (courbes d'impact)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from utils import (
    visuals,
    cohorts,
    rfm as rfm_mod,
    clv as clv_mod,
)

st.set_page_config(page_title="Scénarios CLV - Online Retail II", layout="wide")

# ============================================================================
# HEADER
# ============================================================================

st.title("Simulation de Scénarios CLV")
st.markdown("""
Testez l'impact de différentes actions marketing sur la **Customer Lifetime Value (CLV)**, 
le **Chiffre d'Affaires** et la **Marge**.

**Cas d'usage :**
- Évaluer le ROI d'un programme de fidélisation (+rétention)
- Quantifier l'impact d'une politique de remise
- Optimiser la marge en fonction du taux d'actualisation
""")

# ============================================================================
# FILTRES GLOBAUX
# ============================================================================

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
    st.warning("Aucune donnée disponible avec ces filtres.")
    st.stop()

# ============================================================================
# CALCUL DES MÉTRIQUES DE BASE
# ============================================================================

# Date de snapshot pour RFM
snapshot_date = df["invoicedate"].max() + pd.Timedelta(days=1)

# Calcul RFM pour segmentation
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

# Fusionner les segments dans le DataFrame principal des transactions
# Cela permet d'avoir la colonne 'segment_label' dans df pour les calculs de remise
if "segment_label" not in df.columns:
    # On s'assure que customer_id est disponible pour la fusion
    rfm_to_merge = rfm.reset_index() if "customer_id" not in rfm.columns else rfm
    # On ne garde que les colonnes nécessaires
    if "customer_id" in rfm_to_merge.columns and "segment_label" in rfm_to_merge.columns:
        df = df.merge(rfm_to_merge[["customer_id", "segment_label"]], on="customer_id", how="left")

# Estimation du taux de rétention moyen baseline
df_cohort = cohorts.assign_cohort(df)
retention_table, _ = cohorts.build_retention_table(df_cohort)

if retention_table.shape[1] > 1:
    baseline_retention = retention_table.iloc[:, 1:].stack().mean()
else:
    baseline_retention = 0.5  # Fallback

# Métriques globales baseline
total_revenue = df["revenue"].sum()
total_customers = df["customer_id"].nunique()
avg_revenue_per_customer = total_revenue / total_customers if total_customers > 0 else 0
# Calculs additionnels pour aide à la décision
avg_basket = df.groupby('invoice')['revenue'].sum().mean()

# Calcul de la durée des données en mois pour métriques mensuelles
date_min = df['invoicedate'].min()
date_max = df['invoicedate'].max()
n_months_data = (date_max - date_min).days / 30.44
if n_months_data < 1: n_months_data = 1

avg_monthly_revenue_per_customer = avg_revenue_per_customer / n_months_data

# ============================================================================
# SECTION 1 : PARAMÈTRES DE BASE CLV
# ============================================================================

st.subheader("Paramètres de Base CLV")

st.markdown("""
Ces paramètres définissent le **modèle CLV paramétrique** utilisé pour les simulations.

**Formule CLV :** `CLV = (marge × r) / (1 + d - r)`

Où :
- **marge** = marge moyenne par client et par période (€)
- **r** = taux de rétention (probabilité qu'un client reste actif)
- **d** = taux d'actualisation (décote des flux futurs)
""")

col1, col2, col3 = st.columns(3)

with col1:
    base_margin = st.number_input(
        "Marge moyenne par période (€)",
        min_value=0.0,
        value=30.0,
        step=5.0,
        help=(
            "Marge nette moyenne générée par client et par période (mois).\n\n"
            "**Exemple :** Si un client génère 100€ de CA avec 30% de marge, "
            "la marge mensuelle est 30€."
        ),
    )
    st.caption(
        f"**Repères :**\n"
        f"- Panier Moyen : **{avg_basket:,.0f}€**\n"
        f"- CA / Client : **{avg_revenue_per_customer:,.0f}€**\n"
        f"- CA / Client / Mois : **{avg_monthly_revenue_per_customer:,.0f}€**"
    )

with col2:
    discount_rate = st.number_input(
        "Taux d'actualisation (d)",
        min_value=0.0,
        max_value=1.0,
        value=0.10,
        step=0.01,
        format="%.2f",
        help=(
            "Taux de décote appliqué aux flux futurs.\n\n"
            "**Exemple :** d = 0.10 signifie qu'un euro dans un mois "
            "vaut 0.90€ aujourd'hui."
        ),
    )

with col3:
    st.metric(
        "Rétention moyenne empirique",
        f"{baseline_retention:.1%}",
        help=(
            "Taux de rétention moyen calculé à partir de l'analyse de cohortes.\n\n"
            "Moyenne des taux de rétention observés pour M+1, M+2, M+3, etc."
        ),
    )

# ============================================================================
# SECTION 2 : PARAMÈTRES DU SCÉNARIO
# ============================================================================

st.markdown("---")
st.subheader("Paramètres du Scénario")

st.markdown("""
Ajustez les leviers marketing pour simuler différents scénarios et observer leur impact.
""")

col_a, col_b, col_c = st.columns(3)

with col_a:
    retention_uplift_pct_input = st.slider(
        "Amélioration de la rétention",
        min_value=-50,
        max_value=50,
        value=0,
        step=5,
        format="%d%%",
        help=(
            "Variation relative du taux de rétention.\n\n"
            "**Exemple :** +20% signifie que si r = 60%, le nouveau taux sera 72%.\n\n"
            "**Impact :** Augmente le nombre de clients actifs dans le futur → ↑ CLV"
        ),
    )
    retention_uplift_pct = retention_uplift_pct_input / 100.0
    
    if retention_uplift_pct != 0:
        new_retention = baseline_retention * (1 + retention_uplift_pct)
        st.caption(f"Nouveau taux : {baseline_retention:.1%} → **{new_retention:.1%}**")

with col_b:
    margin_uplift_pct_input = st.slider(
        "Variation de la marge",
        min_value=-50,
        max_value=50,
        value=0,
        step=5,
        format="%d%%",
        help=(
            "Variation relative de la marge moyenne.\n\n"
            "**Exemple :** +10% signifie que si marge = 30€, la nouvelle marge sera 33€.\n\n"
            "**Impact :** Augmente directement la CLV"
        ),
    )
    margin_uplift_pct = margin_uplift_pct_input / 100.0
    
    if margin_uplift_pct != 0:
        new_margin = base_margin * (1 + margin_uplift_pct)
        st.caption(f"Nouvelle marge : {base_margin:.0f}€ → **{new_margin:.0f}€**")

with col_c:
    discount_pct_global_input = st.slider(
        "Remise globale sur le CA",
        min_value=0,
        max_value=50,
        value=0,
        step=5,
        format="%d%%",
        help=(
            "Remise appliquée sur le chiffre d'affaires.\n\n"
            "**Exemple :** 20% signifie -20% sur tous les montants.\n\n"
            "**Impact :** Réduit le CA et la marge"
        ),
    )
    discount_pct_global = discount_pct_global_input / 100.0

# Mode de remise (global ou par segment)
st.markdown("#### Mode d'Application des Remises")

mode_discounts = st.radio(
    "Choix du mode",
    options=["global", "segment"],
    format_func=lambda x: "Remise globale (tous les clients)" if x == "global" else "Remises différenciées par segment RFM",
    help=(
        "**Global :** Même remise pour tous les clients.\n\n"
        "**Par segment :** Remises personnalisées selon le segment RFM "
        "(ex: 5% pour Champions, 20% pour À risque)."
    ),
)

segment_discounts = None
if mode_discounts == "segment":
    st.markdown("##### Paramétrage des remises par segment RFM")
    
    segment_discounts = {}
    segments_sorted = sorted(rfm["segment_label"].dropna().unique())
    
    cols = st.columns(min(3, len(segments_sorted)))
    for idx, seg in enumerate(segments_sorted):
        with cols[idx % 3]:
            discount_val = st.slider(
                f"Remise '{seg}'",
                min_value=0,
                max_value=50,
                value=0,
                step=5,
                format="%d%%",
                key=f"discount_{seg}",
            )
            segment_discounts[seg] = discount_val / 100.0
    
    st.caption(
        "**Exemple :** Appliquer 5% de remise aux 'Champions' pour les fidéliser, "
        "et 20% aux segments 'À risque' pour les réactiver."
    )

# ============================================================================
# SECTION 3 : LANCEMENT DE LA SIMULATION
# ============================================================================

st.markdown("---")

if st.button("Lancer la Simulation", type="primary", use_container_width=True):
    
    with st.spinner("Calcul en cours..."):
        
        # ========================================================================
        # CALCUL DU TAUX DE REMISE EFFECTIF
        # ========================================================================
        
        if mode_discounts == "segment" and segment_discounts:
            # Calculer le CA par segment
            revenue_by_segment = df.groupby("segment_label")["revenue"].sum()
            total_revenue_hist = revenue_by_segment.sum()
            
            total_discount_amount = 0
            for seg, rev in revenue_by_segment.items():
                disc = segment_discounts.get(seg, 0.0)
                total_discount_amount += rev * disc
                
            effective_discount_rate = total_discount_amount / total_revenue_hist if total_revenue_hist > 0 else 0.0
        else:
            effective_discount_rate = discount_pct_global

        # ========================================================================
        # CALCUL CLV PARAMÉTRIQUE
        # ========================================================================
        
        # CLV Baseline
        baseline_clv = clv_mod.clv_parametric(
            margin=base_margin,
            retention_rate=baseline_retention,
            discount_rate=discount_rate
        )
        
        # CLV Scénario
        scenario_retention = baseline_retention * (1 + retention_uplift_pct)
        
        # La marge est impactée par la remise effective
        scenario_margin = base_margin * (1 + margin_uplift_pct) * (1 - effective_discount_rate)
        
        scenario_clv = clv_mod.clv_parametric(
            margin=scenario_margin,
            retention_rate=scenario_retention,
            discount_rate=discount_rate
        )
        
        delta_clv = scenario_clv - baseline_clv
        delta_clv_pct = (delta_clv / baseline_clv * 100) if baseline_clv > 0 else 0
        
        # ========================================================================
        # AFFICHAGE RÉSULTATS CLV PARAMÉTRIQUE
        # ========================================================================
        
        st.success("Simulation terminée !")
        
        st.subheader("Résultats CLV Paramétrique")
        
        col_clv1, col_clv2, col_clv3 = st.columns(3)
        
        with col_clv1:
            st.metric(
                "CLV Baseline",
                f"{baseline_clv:.2f}€",
                help=(
                    "CLV calculée avec les paramètres de base.\n\n"
                    f"Formule : ({base_margin:.0f} × {baseline_retention:.2f}) / "
                    f"(1 + {discount_rate:.2f} - {baseline_retention:.2f})"
                ),
            )
        
        with col_clv2:
            st.metric(
                "CLV Scénario",
                f"{scenario_clv:.2f}€",
                delta=f"{delta_clv:+.2f}€",
                delta_color="normal",
                help=(
                    "CLV calculée avec les paramètres du scénario.\n\n"
                    f"Formule : ({scenario_margin:.2f} × {scenario_retention:.2f}) / "
                    f"(1 + {discount_rate:.2f} - {scenario_retention:.2f})"
                ),
            )
        
        with col_clv3:
            st.metric(
                "Variation CLV",
                f"{delta_clv_pct:+.1f}%",
                delta=f"{delta_clv:+.2f}€",
                delta_color="off",
                help=(
                    "Variation absolue et relative de la CLV.\n\n"
                    "Indique l'impact financier du scénario par client."
                ),
            )
        
        # ========================================================================
        # GRAPHIQUE ÉVOLUTION CA CUMULÉ (12 MOIS)
        # ========================================================================
        
        st.markdown("---")
        st.subheader("Projection du Chiffre d'Affaires Cumulé (12 mois)")
        
        # 1. Calcul du "Run-rate" (CA mensuel moyen historique)
        # On regarde l'étendue des données en mois
        date_min = df['invoicedate'].min()
        date_max = df['invoicedate'].max()
        n_months_data = (date_max - date_min).days / 30.44
        if n_months_data < 1: n_months_data = 1
        
        monthly_run_rate = total_revenue / n_months_data
        
        # 2. Simulation sur 12 mois
        months = list(range(1, 13))
        
        # Baseline : On projette le CA moyen constant (Hypothèse : activité stable)
        baseline_monthly = [monthly_run_rate for _ in months]
        baseline_cumulative = pd.Series(baseline_monthly).cumsum()
        
        # Scénario : 
        # - Impact Remise : Baisse immédiate du CA (1 - discount)
        # - Impact Rétention : Augmentation progressive de la base active
        #   Correction : Au lieu d'une exponentielle explosive, on considère que l'amélioration
        #   de la rétention permet d'augmenter la base client active progressivement
        #   jusqu'à atteindre un gain proportionnel à l'uplift au bout de 12 mois.
        #   Ex: +10% rétention -> On vise +10% de CA mensuel en plus au mois 12.
        
        scenario_monthly = []
        current_revenue_base = monthly_run_rate * (1 - effective_discount_rate)
        
        for m in months:
            # Montée en charge progressive de l'effet rétention
            # Au mois 12, on atteint l'uplift complet (ex: +10% de CA mensuel)
            # C'est une hypothèse conservatrice et réaliste pour une année
            progressive_uplift = retention_uplift_pct * (m / 12.0)
            
            # Facteur multiplicatif (ex: 1.05 au mois 6 pour un uplift de 10%)
            retention_effect = 1 + progressive_uplift
            
            monthly_rev = current_revenue_base * retention_effect
            scenario_monthly.append(monthly_rev)
            
        scenario_cumulative = pd.Series(scenario_monthly).cumsum()
        
        df_projection = pd.DataFrame({
            "Mois": months,
            "Baseline (Activité constante)": baseline_cumulative,
            "Scénario (Projeté)": scenario_cumulative
        })
        
        fig_proj = px.line(
            df_projection,
            x="Mois",
            y=["Baseline (Activité constante)", "Scénario (Projeté)"],
            title=f"Projection CA sur 1 an (Base mensuelle : {monthly_run_rate:,.0f}€)",
            labels={"value": "CA Cumulé (€)", "variable": "Scénario"},
            color_discrete_map={
                "Baseline (Activité constante)": "#636EFA",
                "Scénario (Projeté)": "#00CC96"
            }
        )
        
        # Ajouter les zones de gain/perte
        final_delta = scenario_cumulative.iloc[-1] - baseline_cumulative.iloc[-1]
        fig_proj.add_annotation(
            x=12,
            y=scenario_cumulative.iloc[-1],
            text=f"{final_delta:+,.0f}€",
            showarrow=True,
            arrowhead=1,
            ax=0,
            ay=-40
        )
        
        st.plotly_chart(fig_proj, use_container_width=True)
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.metric("CA Cumulé Baseline (1 an)", f"{baseline_cumulative.iloc[-1]:,.0f}€")
        with col_p2:
            st.metric(
                "CA Cumulé Scénario (1 an)", 
                f"{scenario_cumulative.iloc[-1]:,.0f}€",
                delta=f"{final_delta:+,.0f}€"
            )
        
        # ========================================================================
        # GRAPHIQUE COMPARATIF
        # ========================================================================
        
        st.markdown("---")
        st.subheader("Comparaison Baseline vs Scénario")
        
        df_comparison = pd.DataFrame([
            {
                "Métrique": "CLV Moyenne (€)",
                "Baseline": baseline_clv,
                "Scénario": scenario_clv,
            },
        ])
        
        fig_comparison = go.Figure()
        
        fig_comparison.add_trace(go.Bar(
            name='Baseline',
            x=df_comparison['Métrique'],
            y=df_comparison['Baseline'],
            marker_color='#636EFA',
            text=df_comparison['Baseline'].apply(lambda x: f"{x:,.1f}"),
            textposition='outside',
        ))
        
        fig_comparison.add_trace(go.Bar(
            name='Scénario',
            x=df_comparison['Métrique'],
            y=df_comparison['Scénario'],
            marker_color='#00CC96',
            text=df_comparison['Scénario'].apply(lambda x: f"{x:,.1f}"),
            textposition='outside',
        ))
        
        fig_comparison.update_layout(
            title="Baseline vs Scénario",
            barmode='group',
            yaxis_title="Valeur (€)",
            height=400,
            showlegend=True,
        )
        
        st.plotly_chart(fig_comparison, use_container_width=True)
        visuals.download_fig_button(fig_comparison, "comparison_baseline_scenario.png")
        
        # ========================================================================
        # COURBE DE SENSIBILITÉ CLV(r)
        # ========================================================================
        
        st.markdown("---")
        st.subheader("Courbe de Sensibilité : CLV en fonction de la Rétention")
        
        st.markdown("""
        Cette courbe montre comment la CLV évolue en fonction du taux de rétention (r).
        
        **Utilité :** Identifier le ROI potentiel d'actions de fidélisation.
        """)
        
        sens_df = clv_mod.clv_sensitivity_curve(
            margin=scenario_margin,
            discount_rate=discount_rate,
            r_min=max(0.05, baseline_retention * 0.5),
            r_max=min(0.99, baseline_retention * 1.5),
            n_points=50,
        )
        
        fig_sens = px.line(
            sens_df,
            x="retention_rate",
            y="clv",
            title="CLV en fonction du taux de rétention (r)",
            labels={
                "retention_rate": "Taux de rétention (r)",
                "clv": "CLV (€)"
            },
        )
        
        # Ligne verticale pour baseline
        fig_sens.add_vline(
            x=baseline_retention,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Baseline ({baseline_retention:.1%})",
            annotation_position="top",
        )
        
        # Ligne verticale pour scénario
        if retention_uplift_pct != 0:
            fig_sens.add_vline(
                x=scenario_retention,
                line_dash="dash",
                line_color="green",
                annotation_text=f"Scénario ({scenario_retention:.1%})",
                annotation_position="bottom",
            )
        
        fig_sens.update_xaxes(tickformat=".0%")
        fig_sens.update_layout(height=500)
        
        st.plotly_chart(fig_sens, use_container_width=True)
        visuals.download_fig_button(fig_sens, "sensibilite_clv_retention.png")
        
        st.info(
            "**Lecture :** Si le taux de rétention passe de 60% à 70%, "
            "la CLV peut augmenter significativement. Cette courbe aide à évaluer "
            "le ROI attendu d'actions de fidélisation."
        )
        
        # ========================================================================
        # DÉTAILS DE LA SIMULATION
        # ========================================================================
        
        with st.expander("Détails de la Simulation"):
            st.markdown("### Paramètres Utilisés")
            
            col_det1, col_det2 = st.columns(2)
            
            with col_det1:
                st.markdown("**Baseline**")
                st.write(f"- Marge : {base_margin:.2f}€")
                st.write(f"- Rétention : {baseline_retention:.2%}")
                st.write(f"- Actualisation : {discount_rate:.2%}")
                st.write(f"- Remise : 0%")
            
            with col_det2:
                st.markdown("**Scénario**")
                st.write(f"- Marge : {scenario_margin:.2f}€ ({margin_uplift_pct:+.0%})")
                st.write(f"- Rétention : {scenario_retention:.2%} ({retention_uplift_pct:+.0%})")
                st.write(f"- Actualisation : {discount_rate:.2%}")
                st.write(f"- Remise Moyenne : {effective_discount_rate:.1%}")
            
            st.markdown("### Formule CLV Utilisée")
            st.latex(r"CLV = \frac{marge \times r}{1 + d - r}")
            
            st.markdown("""
            Où :
            - **marge** = marge moyenne par période (€)
            - **r** = taux de rétention (probabilité de rester actif)
            - **d** = taux d'actualisation (décote des flux futurs)
            """)

else:
    st.info("Configurez les paramètres ci-dessus puis cliquez sur **Lancer la Simulation**")

# ============================================================================
# AIDE ET DÉFINITIONS
# ============================================================================

st.markdown("---")
with st.expander("Aide et Définitions"):
    st.markdown("""
    ### Définitions des Métriques
    
    **CLV (Customer Lifetime Value) :**
    - Valeur totale qu'un client génère sur toute sa durée de vie
    - Unité : € par client
    - Exemple : CLV = 150€ signifie qu'un client rapporte en moyenne 150€ de marge
    
    **Taux de Rétention (r) :**
    - Probabilité qu'un client reste actif d'une période à l'autre
    - Unité : % (entre 0% et 100%)
    - Exemple : r = 70% signifie que 70% des clients actifs en M+0 le restent en M+1
    
    **Taux d'Actualisation (d) :**
    - Décote appliquée aux flux futurs (valeur temps de l'argent)
    - Unité : % par période
    - Exemple : d = 10% signifie qu'un euro dans un mois vaut 0.90€ aujourd'hui
    
    **Marge :**
    - Profit net généré par client et par période
    - Unité : € par client par période
    - Exemple : Marge = 30€ signifie 30€ de profit par client par mois
    
    ### Cas d'Usage
    
    **1. Évaluer un programme de fidélisation**
    - Hypothèse : +10% de rétention grâce à un programme de fidélité
    - Coût : 5€ par client (réduction de marge)
    - Simulation : Rétention +10%, Marge -16.7%
    - Résultat : Si Δ CLV > 0, le programme est rentable
    
    **2. Tester une politique de remise**
    - Hypothèse : -15% de remise pour booster les ventes
    - Impact : Baisse de marge mais potentielle hausse de rétention
    - Simulation : Remise 15%, Rétention +5%
    - Résultat : Comparer Δ CLV totale vs coût de la remise
    
    **3. Optimiser le taux d'actualisation**
    - Utiliser la courbe de sensibilité pour identifier le taux de rétention cible
    - Déterminer le budget maximal pour atteindre ce taux
    """)
