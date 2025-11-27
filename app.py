import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# On configure la page
st.set_page_config(
    page_title="Tableau de Bord Marketing - Scénarios",
    page_icon="📊",
    layout="wide"
)

#  charger et préparer les données
@st.cache_data
def load_data():
    try:
        # charger les données
        df = pd.read_parquet("data/processed/online_retail_clean.parquet")
        
        
        df = df.rename(columns={
            'Customer ID': 'CustomerID',
            'Price': 'UnitPrice',
            'Invoice': 'InvoiceNo'
        })
        
        # Création de la colonne Total si elle n'existe pas
        if 'Total' not in df.columns and all(col in df.columns for col in ['Quantity', 'UnitPrice']):
            df['Total'] = df['Quantity'] * df['UnitPrice']
            
        # Créer les cohortes à partir de la date de facture
        if 'InvoiceDate' in df.columns:
            df['Cohort'] = pd.to_datetime(df['InvoiceDate']).dt.to_period('M').astype(str)
        else:
            df['Cohort'] = 'Toutes'
            
        # Créer des segments RFM si nécessaire
        if 'RFM_Segment' not in df.columns:
            df['RFM_Segment'] = 'Aucun segment'
            
        return df
        
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {str(e)}")
        
        return pd.DataFrame({
            'Cohort': [],
            'RFM_Segment': [],
            'Total': [],
            'CustomerID': [],
            'InvoiceDate': pd.to_datetime([])
        })

# Fonction pour calculer la CLV
def calculate_clv(df, retention_rate, discount_rate, avg_purchase_value, avg_purchase_freq, customer_lifespan):
    if retention_rate == 0 or discount_rate == 0:
        return 0
    clv = (avg_purchase_value * avg_purchase_freq * retention_rate) / (1 + discount_rate - retention_rate)
    return clv * customer_lifespan

# Fonction principale de la page Scénarios
def show_scenarios():
    st.title("📈 Simulation d'Impact Marketing")
    st.markdown("""
    Cette page vous permet de simuler l'impact de différentes stratégies marketing sur la CLV, le CA et la rétention.
    """)

    # Charger les données
    df = load_data()
    
   
    with st.sidebar:
        st.header("Paramètres de Simulation")
        
        # Sélecteur de cohorte
        cohort_options = ["Toutes les cohortes"] + sorted(df['Cohort'].unique().tolist())
        selected_cohort = st.selectbox(
            "Cohorte cible",
            options=cohort_options,
            index=0
        )
        
        # Paramètres de simulation
        st.subheader("Paramètres Financiers")
        marge = st.slider(
            "Marge brute moyenne (%)",
            min_value=0.0,
            max_value=100.0,
            value=30.0,
            step=0.5,
            help="Marge brute moyenne sur les ventes"
        )
        
        remise = st.slider(
            "Remise moyenne (%)",
            min_value=0.0,
            max_value=100.0,
            value=10.0,
            step=1.0,
            help="Pourcentage de remise à appliquer"
        )
        
        # Option d'application de la remise
        remise_application = st.radio(
            "Appliquer la remise à :",
            ["Tous les clients", "Segments spécifiques"],
            index=0
        )
        
        if remise_application == "Segments spécifiques":
            segments = st.multiselect(
                "Sélectionnez les segments :",
                options=df['RFM_Segment'].unique(),
                default=df['RFM_Segment'].unique()[:2]
            )
        
        st.subheader("Paramètres de Rétention")
        retention_rate = st.slider(
            "Taux de rétention annuel (%)",
            min_value=0.0,
            max_value=100.0,
            value=70.0,
            step=1.0,
            help="Pourcentage de clients qui restent d'une année sur l'autre"
        )
        
        st.subheader("Paramètres de Calcul de la CLV")
        discount_rate = st.slider(
            "Taux d'actualisation annuel (%)",
            min_value=0.0,
            max_value=30.0,
            value=10.0,
            step=0.5,
            help="Taux utilisé pour actualiser les flux de trésorerie futurs"
        )
        
        # Options d'affichage
        st.subheader("Options d'Affichage")
        include_returns = st.checkbox(
            "Inclure les retours",
            value=True,
            help="Inclure les retours dans les calculs"
        )
    
    # Section des résultats
    st.header("Résultats de la Simulation")
    
    # Calculs de base
    if not include_returns:
        df = df[df['Quantity'] > 0]
    
    # Calcul des métriques de base
    if 'CustomerID' in df.columns and not df['CustomerID'].isna().all():
        total_customers = df['CustomerID'].nunique()
    else:
        # Si pas de CustomerID, on utilise un faux compteur  basé sur les factures uniques
        total_customers = len(df['InvoiceNo'].unique()) if 'InvoiceNo' in df.columns else 100
        st.warning("Avertissement : Aucun identifiant client trouvé. Les calculs utilisent le nombre de factures uniques comme estimation.")
    
    # Calcul du chiffre d'affaires total
    if 'Total' in df.columns:
        total_revenue = df['Total'].sum()
        avg_order_value = df['Total'].mean()
    elif all(col in df.columns for col in ['Quantity', 'UnitPrice']):
        # Calcul du total si les colonnes Quantity et UnitPrice existent
        df['Total'] = df['Quantity'] * df['UnitPrice']
        total_revenue = df['Total'].sum()
        avg_order_value = df['Total'].mean()
        st.warning("Avertissement : La colonne Total a été calculée à partir de Quantity * UnitPrice.")
    else:
        # Estimation si les colonnes nécessaires sont manquantes
        total_revenue = 100000  # Valeur par défaut
        avg_order_value = 50    # Valeur par défaut
        st.warning("Avertissement : Impossible de calculer le chiffre d'affaires. Utilisation de valeurs par défaut.")
    
    # Calcul de la CLV de base
    avg_purchase_freq = 12  # À adapter selon vos données
    customer_lifespan = 3   # En années
    
    clv_baseline = calculate_clv(
        df, 
        retention_rate/100, 
        discount_rate/100, 
        avg_order_value, 
        avg_purchase_freq, 
        customer_lifespan
    )
    
    # Calcul des métriques avec le scénario
    new_retention = min(100, retention_rate + 5)  
    new_avg_order_value = avg_order_value * (1 - remise/100)
    
    clv_scenario = calculate_clv(
        df,
        new_retention/100,
        discount_rate/100,
        new_avg_order_value,
        avg_purchase_freq,
        customer_lifespan
    )
    
    # Affichage des KPI
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "CLV Actuelle",
            f"{clv_baseline:,.2f} €",
            delta=None,
            help="Valeur à vie du client actuelle"
        )
    
    with col2:
        st.metric(
            "CLV avec Scénario",
            f"{clv_scenario:,.2f} €",
            delta=f"{(clv_scenario - clv_baseline):,.2f} €",
            delta_color="inverse" if clv_scenario < clv_baseline else "normal",
            help="Valeur à vie du client avec les paramètres du scénario"
        )
    
    with col3:
        impact_pct = ((clv_scenario - clv_baseline) / clv_baseline * 100) if clv_baseline != 0 else 0
        st.metric(
            "Impact sur la CLV",
            f"{impact_pct:+.2f}%",
            delta=None,
            help="Variation en pourcentage de la CLV"
        )
    
    # Graphique d'impact
    st.subheader("Impact des Paramètres sur la CLV")
    
    # Simulation de sensibilité
    retention_rates = np.linspace(0.1, 1, 10)  # 10% à 100%
    clv_values = [calculate_clv(df, r, discount_rate/100, new_avg_order_value, avg_purchase_freq, customer_lifespan) 
                 for r in retention_rates]
    
    fig = px.line(
        x=retention_rates*100, 
        y=clv_values,
        labels={'x': 'Taux de Rétention (%)', 'y': 'CLV (€)'},
        title='Sensibilité de la CLV au Taux de Rétention',
        markers=True
    )
    
    # Ajout d'une ligne pour la valeur actuelle
    fig.add_hline(
        y=clv_baseline, 
        line_dash="dash", 
        line_color="red",
        annotation_text=f"CLV Actuelle: {clv_baseline:,.2f} €",
        annotation_position="bottom right"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tableau récapitulatif
    st.subheader("Récapitulatif des Paramètres")
    
    summary_data = {
        'Paramètre': [
            'Cohorte sélectionnée',
            'Marge brute moyenne',
            'Remise appliquée',
            'Taux de rétention',
            'Taux d\'actualisation',
            'Retours inclus',
            'Application de la remise'
        ],
        'Valeur': [
            selected_cohort,
            f"{marge}%",
            f"{remise}%",
            f"{retention_rate}%",
            f"{discount_rate}%",
            "Oui" if include_returns else "Non",
            remise_application
        ]
    }
    
    st.table(pd.DataFrame(summary_data))
    
    # Bouton d'export
    if st.button("Exporter les Résultats"):
        # Création d'un DataFrame pour l'export
        export_data = {
            'Métrique': ['CLV Actuelle', 'CLV avec Scénario', 'Impact'],
            'Valeur (€)': [clv_baseline, clv_scenario, clv_scenario - clv_baseline],
            'Valeur (%)': [100, (clv_scenario/clv_baseline)*100 if clv_baseline != 0 else 0, 
                         ((clv_scenario - clv_baseline)/clv_baseline)*100 if clv_baseline != 0 else 0]
        }
        
        df_export = pd.DataFrame(export_data)
        
        # Export en CSV
        csv = df_export.to_csv(index=False).encode('utf-8')
        
        # Téléchargement du fichier
        st.download_button(
            label="Télécharger les résultats en CSV",
            data=csv,
            file_name=f"simulation_clv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime='text/csv',
        )

# Point d'entrée de l'application
if _name_ == "_main_":
    show_scenarios()
