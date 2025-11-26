# utils/visuals.py

"""
visuals.py
---------------------------------
Helpers pour l'app Streamlit :

- Chargement & préparation des données (avec cache)
- Filtres globaux (sidebar)
- Cartes KPI stylisées
- Helpers de charts + export PNG
"""

from __future__ import annotations

from io import BytesIO
from typing import Dict, Tuple, Optional, List

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import data_loader, preprocessing


# -------------------------------------------------------------------
# 1. CHARGEMENT & PRÉPARATION
# -------------------------------------------------------------------

DATA_PATH = "data/raw/online_retail_II.csv"


@st.cache_data(show_spinner=True)
def load_raw_data(path: str = DATA_PATH) -> pd.DataFrame:
    df_raw = pd.read_csv(path)
    df_raw = data_loader.normalize_columns(df_raw)
    return df_raw


@st.cache_data(show_spinner=True)
def get_prepared_data(
    returns_policy: str = "include",
    drop_customers_na: bool = True,
) -> pd.DataFrame:
    df_raw = load_raw_data(DATA_PATH)
    df_prep = preprocessing.prepare_base_dataframe(
        df_raw,
        drop_customers_na=drop_customers_na,
        returns_policy=returns_policy,
    )
    return df_prep


# -------------------------------------------------------------------
# 2. UI : CARTES KPI + BADGES
# -------------------------------------------------------------------

def format_number(v: float, decimals: int = 0, unit: str | None = None) -> str:
    if v is None:
        return "-"
    if decimals == 0:
        s = f"{v:,.0f}".replace(",", " ")
    else:
        s = f"{v:,.{decimals}f}".replace(",", " ")
    if unit:
        return f"{s} {unit}"
    return s


def kpi_card(
    label: str,
    value: float | int | str,
    delta: Optional[float] = None,
    unit: Optional[str] = None,
    help_text: Optional[str] = None,
    decimals: int = 0,
):

    # Format value proprement
    if isinstance(value, (int, float)):
        value_str = format_number(value, decimals=decimals, unit=unit)
    else:
        value_str = str(value)

    # Delta optionnel
    delta_html = ""
    if isinstance(delta, (int, float)):
        sign = "▲" if delta >= 0 else "▼"
        color = "#16a34a" if delta >= 0 else "#dc2626"
        delta_html = (
            f"<div style='font-size:0.8rem;color:{color};margin-top:0.1rem'>"
            f"{sign} {delta:.1%}</div>"
        )

    # HTML PROPRE, SANS CONTENEUR INUTILE
    card_html = f"""
        <div style="
            background: #ffffff;
            border-radius: 0.9rem;
            padding: 1rem;
            box-shadow: 0 2px 6px rgba(15,23,42,0.06);
            border: 1px solid rgba(148,163,184,0.4);
        ">
            <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">
                {label}
            </div>
            <div style="font-size:1.3rem;font-weight:600;color:#0f172a;margin-top:0.2rem;">
                {value_str}
            </div>
            {delta_html}
        </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)

    if help_text:
        st.caption("ℹ️ " + help_text)





def badge(text: str, color: str = "#e2e8f0", text_color: str = "#0f172a"):
    st.markdown(
        f"""
        <span style="
            display:inline-flex;
            align-items:center;
            padding:0.15rem 0.55rem;
            border-radius:999px;
            background:{color};
            color:{text_color};
            font-size:0.72rem;
            margin-right:0.25rem;
            margin-bottom:0.25rem;
        ">{text}</span>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------
# 3. FILTRES GLOBAUX (SIDEBAR)
# -------------------------------------------------------------------

def render_global_sidebar(
    returns_policy_default: str = "include",
) -> Dict:

    with st.sidebar:
        st.markdown("### 🎚️ Filtres globaux")

        st.markdown("#### Données & retours")
        returns_policy = st.radio(
            "Politique sur les retours",
            options=["include", "exclude", "neutralize"],
            index=["include", "exclude", "neutralize"].index(returns_policy_default),
        )

    # Charger dataset pour bornes dynamiques
    df_all = get_prepared_data(returns_policy=returns_policy, drop_customers_na=False)

    min_date = df_all["invoicedate"].min().date()
    max_date = df_all["invoicedate"].max().date()

    # OPTIONS dynamiques basées sur le dataset réel
    relative_ranges = {
        "Toute la période": (min_date, max_date),
        "Dernier mois": (max_date - pd.DateOffset(months=1), max_date),
        "Derniers 3 mois": (max_date - pd.DateOffset(months=3), max_date),
        "Derniers 6 mois": (max_date - pd.DateOffset(months=6), max_date),
        "Dernière année": (max_date - pd.DateOffset(years=1), max_date),
        "Personnalisé": None,
    }

    with st.sidebar:
        choice = st.selectbox(
            "Période",
            list(relative_ranges.keys()),
            help="Selectionne une période relative ou définis une fenêtre personnalisée."
        )

        if choice != "Personnalisé":
            start, end = relative_ranges[choice]

            # Convertir Timestamp → date pour éviter les erreurs
            if hasattr(start, "date"):
                start = start.date()
            if hasattr(end, "date"):
                end = end.date()

            # Tronquer aux bornes réelles
            if start < min_date:
                start = min_date
            if end > max_date:
                end = max_date

            date_range = (start, end)


        else:
            # Sélection manuelle
            date_range = st.date_input(
                "Sélection personnalisée",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )

            start_date, end_date = date_range

            # Sécurisation
            if start_date < min_date:
                start_date = min_date
            if end_date > max_date:
                end_date = max_date
            if start_date > end_date:
                start_date, end_date = min_date, max_date

            date_range = (start_date, end_date)

        # FILTRE PAYS – aucun default
        countries = sorted(df_all["country"].dropna().unique().tolist())

        selected_countries = st.multiselect(
            "Pays",
            options=countries,
            default=[],   # <- suppression du default UK
        )

        st.markdown("---")
        drop_customers_na = st.checkbox(
            "Exclure les lignes sans Customer ID",
            value=True,
        )

    return {
        "returns_policy": returns_policy,
        "date_range": date_range,
        "countries": selected_countries,
        "drop_customers_na": drop_customers_na,
    }


# -------------------------------------------------------------------
# 4. APPLICATION FILTRES
# -------------------------------------------------------------------

def apply_filters(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    df = df.copy()

    date_min, date_max = filters["date_range"]
    mask_date = (df["invoicedate"].dt.date >= date_min) & (df["invoicedate"].dt.date <= date_max)

    if filters["countries"]:
        mask_country = df["country"].isin(filters["countries"])
    else:
        mask_country = True

    df = df[mask_date & mask_country].copy()
    return df


# -------------------------------------------------------------------
# 5. CHARTS + EXPORT PNG
# -------------------------------------------------------------------

def fig_to_png_bytes(fig) -> bytes:
    buf = BytesIO()
    fig.write_image(buf, format="png")
    buf.seek(0)
    return buf.read()


def download_fig_button(fig, filename: str, label: str = "⬇️ Export PNG"):
    try:
        png_bytes = fig_to_png_bytes(fig)
        st.download_button(label=label, data=png_bytes, file_name=filename, mime="image/png")
    except Exception as e:
        st.caption(f"⚠️ Export PNG indisponible : {e}")


def line_chart(df: pd.DataFrame, x: str, y: str, title: str,
               yaxis_title: Optional[str] = None,
               xaxis_title: Optional[str] = None):
    fig = px.line(df, x=x, y=y, markers=True)
    fig.update_layout(title=title, hovermode="x unified")
    if xaxis_title:
        fig.update_xaxes(title=xaxis_title)
    if yaxis_title:
        fig.update_yaxes(title=yaxis_title)

    st.plotly_chart(fig, use_container_width=True)
    download_fig_button(fig, f"{title}.png")
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str, orientation: str = "v"):
    if orientation == "h":
        fig = px.bar(df, x=y, y=x, orientation="h")
    else:
        fig = px.bar(df, x=x, y=y)

    fig.update_layout(title=title)
    st.plotly_chart(fig, use_container_width=True)
    download_fig_button(fig, f"{title}.png")
    return fig


def render_active_filters(filters: Dict):
    st.markdown("#### 🎯 Filtres actifs")

    date_min, date_max = filters["date_range"]
    badge(f"Période : {date_min} → {date_max}")

    # Pays
    if filters["countries"]:
        if len(filters["countries"]) == 1:
            badge(f"Pays : {filters['countries'][0]}")
        else:
            badge(f"Pays : {len(filters['countries'])} pays sélectionnés")
    else:
        badge("Pays : tous")

    # Politique retours
    badge(
        {
            "include": "Retours : inclus",
            "exclude": "Retours : exclus",
            "neutralize": "Retours : neutralisés",
        }[filters["returns_policy"]],
        color="#fee2e2" if filters["returns_policy"] == "include" else "#dcfce7",
        text_color="#b91c1c" if filters["returns_policy"] == "include" else "#166534",
    )

    # Option clients anonymes
    if filters["drop_customers_na"]:
        badge("Clients : ID requis", color="#e0f2fe", text_color="#075985")
    else:
        badge("Clients : anonymes inclus", color="#e5e7eb", text_color="#374151")
