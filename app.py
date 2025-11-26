# app/app.py
import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from utils import cohort_retention

st.set_page_config(page_title="Marketing Analytics", layout="wide")

st.title("Cohortes d'Acquisition — Dashboard Marketing")

# Upload dataset
file = st.sidebar.file_uploader("Uploader le fichier Online Retail II", type=["csv"])

if file:
    df = pd.read_csv(file)
    
    st.sidebar.success("Dataset chargé ✔")

    # Conversion TotalPrice si besoin
    if "TotalPrice" not in df.columns:
        df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]

    st.header(" Heatmap de rétention par cohorte")

    retention = cohort_retention(df)

    fig, ax = plt.subplots(figsize=(14, 6))
    sns.heatmap(
        retention,
        annot=True,
        fmt=".0%",
        cmap="Blues",
        ax=ax
    )
    ax.set_title("Rétention par cohorte (M+0, M+1, …)")
    ax.set_xlabel("Âge de cohorte (mois)")
    ax.set_ylabel("Mois d’acquisition")

    st.pyplot(fig)

    # KPIs rapides
    st.header(" KPIs")
    col1, col2 = st.columns(2)
    col1.metric("Cohortes analysées", len(retention), help="Nombre total de cohortes d'acquisition.")
    col2.metric("Rétention moyenne M+1", f"{retention[1].mean():.1%}", help="Part des clients revenant le mois suivant.")
    
else:
    st.info("Veuillez uploader le fichier CSV pour commencer.")
