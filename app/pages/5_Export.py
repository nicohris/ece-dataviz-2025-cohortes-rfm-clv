# app/pages/5_📤_Export.py

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from utils import (
    visuals,
    cohorts,
    rfm as rfm_mod,
)

st.set_page_config(page_title="Export - Online Retail II", layout="wide")

st.title("Export de données")

filters = visuals.render_global_sidebar()
df = visuals.get_prepared_data(
    returns_policy=filters["returns_policy"],
    drop_customers_na=False,
)
df = visuals.apply_filters(df, filters)

visuals.render_active_filters(filters)
st.markdown("---")

if df.empty:
    st.warning("Aucune donnée à exporter avec les filtres actuels.")
    st.stop()

# -------------- Export des transactions filtrées --------------
st.subheader("Transactions filtrées")

csv_tx = df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Exporter les transactions filtrées (CSV)",
    data=csv_tx,
    file_name="transactions_filtrees.csv",
    mime="text/csv",
)
st.caption(
    "Inclut l'ensemble des variables de base (Invoice, StockCode, Quantity, Price, etc.) "
    "et les variables dérivées (Revenue, is_return, …) pour la fenêtre et les pays sélectionnés."
)

# -------------- Export RFM --------------
st.markdown("---")
st.subheader("Table RFM")

df_rfm_source = df[df["customer_id"].notna()].copy()
if df_rfm_source.empty:
    st.info("Pas de clients identifiés dans le périmètre actuel, impossible de générer la table RFM.")
else:
    snapshot_date = df_rfm_source["invoicedate"].max() + pd.Timedelta(days=1)
    rfm = rfm_mod.compute_rfm(
        df_rfm_source,
        snapshot_date=snapshot_date,
        customer_col="customer_id",
        date_col="invoicedate",
        invoice_col="invoice",
        revenue_col="revenue",
    )
    rfm = rfm_mod.score_rfm(rfm)
    rfm = rfm_mod.label_rfm_segments(rfm)

    csv_rfm = rfm.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Exporter la table RFM (CSV)",
        data=csv_rfm,
        file_name="rfm_table.csv",
        mime="text/csv",
    )
    st.caption(
        "Contient pour chaque client : Recency (jours), Frequency (nb de factures), "
        "Monetary (CA total), scores R/F/M (1–5) et label de segment marketing."
    )

# -------------- Export tables cohortes --------------
st.markdown("---")
st.subheader("Tables de cohortes (rétention & CA)")

df_cohort_src = df[df["customer_id"].notna()].copy()
if df_cohort_src.empty:
    st.info("Pas de clients identifiés dans le périmètre actuel, impossible de générer les tables de cohortes.")
else:
    df_cohort = cohorts.assign_cohort(df_cohort_src)
    retention_table, counts_table = cohorts.build_retention_table(df_cohort)
    revenue_table, revenue_cum_table = cohorts.build_revenue_tables(df_cohort)

    csv_retention = retention_table.to_csv().encode("utf-8")
    csv_counts = counts_table.to_csv().encode("utf-8")
    csv_rev = revenue_table.to_csv().encode("utf-8")
    csv_rev_cum = revenue_cum_table.to_csv().encode("utf-8")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Retention table (CSV)",
            data=csv_retention,
            file_name="cohort_retention_table.csv",
            mime="text/csv",
        )
        st.download_button(
            "Counts table (CSV)",
            data=csv_counts,
            file_name="cohort_counts_table.csv",
            mime="text/csv",
        )
    with col2:
        st.download_button(
            "Revenue table (CSV)",
            data=csv_rev,
            file_name="cohort_revenue_table.csv",
            mime="text/csv",
        )
        st.download_button(
            "Revenue cumulative (CSV)",
            data=csv_rev_cum,
            file_name="cohort_revenue_cum_table.csv",
            mime="text/cv",
        )

    st.caption(
        "Ces tables permettent de refaire des analyses de rétention, de valeur cumulée "
        "et de CLV empirique hors de l'application (Excel, BI, notebooks…)."
    )
