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
        sign = "+" if delta >= 0 else "-"
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
        st.caption(help_text)





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
        st.markdown("### Filtres globaux")

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


def download_fig_button(fig, filename: str, label: str = "Export PNG"):
    try:
        png_bytes = fig_to_png_bytes(fig)
        st.download_button(label=label, data=png_bytes, file_name=filename, mime="image/png")
    except Exception as e:
        st.caption(f"Export PNG indisponible : {e}")


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


def map_chart(df: pd.DataFrame, title: str = "Carte des commandes"):
    import folium
    from folium import plugins
    from streamlit_folium import st_folium
    
    # Agrégation par pays avec codes ISO
    country_stats = (
        df.groupby("country")
        .agg(
            revenue=("revenue", "sum"),
            count=("invoice", "nunique"),
            customers=("customer_id", "nunique")
        )
        .reset_index()
    )

    if country_stats.empty:
        st.info("Pas de données géographiques à afficher.")
        return

    # Mapping des pays vers leurs coordonnées (latitude, longitude)
    # Pour les principaux pays européens
    country_coords = {
        "United Kingdom": [54.0, -2.0],
        "France": [46.0, 2.0],
        "Germany": [51.0, 9.0],
        "Spain": [40.0, -4.0],
        "Italy": [42.8, 12.8],
        "Netherlands": [52.3, 5.5],
        "Belgium": [50.8, 4.3],
        "Switzerland": [46.8, 8.2],
        "Portugal": [39.5, -8.0],
        "Austria": [47.5, 14.5],
        "Sweden": [62.0, 15.0],
        "Norway": [60.5, 8.5],
        "Denmark": [56.0, 10.0],
        "Finland": [64.0, 26.0],
        "Poland": [52.0, 19.0],
        "Ireland": [53.0, -8.0],
        "Greece": [39.0, 22.0],
        "Czech Republic": [49.8, 15.5],
        "Australia": [-25.0, 133.0],
        "Japan": [36.0, 138.0],
        "USA": [37.0, -95.0],
        "Canada": [56.0, -106.0],
        "EIRE": [53.0, -8.0],
        "Channel Islands": [49.2, -2.1],
        "Iceland": [64.9, -19.0],
        "Cyprus": [35.1, 33.4],
        "Malta": [35.9, 14.4],
        "Lithuania": [55.2, 23.9],
        "Latvia": [56.9, 24.6],
        "Estonia": [58.6, 25.0],
        "Slovakia": [48.7, 19.7],
        "Hungary": [47.2, 19.5],
        "Romania": [45.9, 24.9],
        "Bulgaria": [42.7, 25.5],
        "Croatia": [45.8, 16.0],
        "Slovenia": [46.1, 14.8],
        "Serbia": [44.0, 21.0],
        "Lebanon": [33.9, 35.5],
        "United Arab Emirates": [24.0, 54.0],
        "Israel": [31.5, 34.8],
        "Saudi Arabia": [24.0, 45.0],
        "Brazil": [-10.0, -55.0],
        "Singapore": [1.3, 103.8],
        "Hong Kong": [22.3, 114.2],
        "South Africa": [-29.0, 24.0],
        "Bahrain": [26.0, 50.5],
        "RSA": [-29.0, 24.0],
    }

    # Créer la carte centrée sur l'Europe
    m = folium.Map(
        location=[50.0, 10.0],
        zoom_start=4,
        tiles=None,  # On va ajouter nos propres tiles
        control_scale=True,
        prefer_canvas=True
    )

    # Ajouter plusieurs couches de tuiles (satellite, street, etc.)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles='OpenStreetMap',
        name='Street Map',
        overlay=False,
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles='CartoDB positron',
        name='Light',
        overlay=False,
        control=True
    ).add_to(m)

    # Normaliser les revenus pour la taille des cercles
    max_revenue = country_stats['revenue'].max()
    min_revenue = country_stats['revenue'].min()
    
    # Ajouter les marqueurs pour chaque pays
    for _, row in country_stats.iterrows():
        country = row['country']
        if country in country_coords:
            coords = country_coords[country]
            revenue = row['revenue']
            
            # Calculer la taille du cercle (entre 10 et 50)
            if max_revenue > min_revenue:
                normalized = (revenue - min_revenue) / (max_revenue - min_revenue)
                radius = 10 + (normalized * 40)
            else:
                radius = 25
            
            # Calculer la couleur (du bleu au rouge)
            if max_revenue > min_revenue:
                normalized = (revenue - min_revenue) / (max_revenue - min_revenue)
                # Gradient de couleur
                if normalized < 0.33:
                    color = '#3b82f6'  # Bleu
                elif normalized < 0.66:
                    color = '#f59e0b'  # Orange
                else:
                    color = '#ef4444'  # Rouge
            else:
                color = '#3b82f6'
            
            # Créer le popup
            popup_html = f"""
            <div style="font-family: Inter, sans-serif; min-width: 200px;">
                <h4 style="margin: 0 0 10px 0; color: #0f172a;">{country}</h4>
                <p style="margin: 5px 0;"><strong>CA:</strong> {revenue:,.0f}€</p>
                <p style="margin: 5px 0;"><strong>Commandes:</strong> {row['count']:,}</p>
                <p style="margin: 5px 0;"><strong>Clients:</strong> {row['customers']:,}</p>
            </div>
            """
            
            folium.CircleMarker(
                location=coords,
                radius=radius,
                popup=folium.Popup(popup_html, max_width=300),
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2,
                opacity=0.9
            ).add_to(m)

    # Ajouter un contrôle de couches
    folium.LayerControl().add_to(m)
    
    # Ajouter un plugin de plein écran
    plugins.Fullscreen(
        position='topright',
        title='Plein écran',
        title_cancel='Quitter le plein écran',
        force_separate_button=True
    ).add_to(m)

    # Afficher la carte dans Streamlit
    st.markdown(f"### {title}")
    st_folium(m, width=None, height=600, returned_objects=[])
    
    return m


def render_active_filters(filters: Dict):
    st.markdown("#### Filtres actifs")

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
