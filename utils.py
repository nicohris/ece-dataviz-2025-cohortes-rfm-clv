# app/utils.py
import pandas as pd
import numpy as np


def assign_cohort(df):
    """
    Ajoute deux colonnes :
    - CohortMonth : mois d'acquisition du client
    - InvoiceMonth : mois de la transaction
    """
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["InvoiceMonth"] = df["InvoiceDate"].dt.to_period("M")
    
    cohort = df.groupby("CustomerID")["InvoiceMonth"].min()
    cohort.name = "CohortMonth"
    
    df = df.join(cohort, on="CustomerID")
    return df


def cohort_retention(df):
    """
    Retourne une matrice cohorte x âge (M+0, M+1, …)
    avec la rétention en %.
    """
    df = assign_cohort(df)
    
    df["CohortIndex"] = (
        (df["InvoiceMonth"].dt.year - df["CohortMonth"].dt.year) * 12 +
        (df["InvoiceMonth"].dt.month - df["CohortMonth"].dt.month)
    )

    cohort_sizes = (
        df[df["CohortIndex"] == 0]
        .groupby("CohortMonth")["CustomerID"]
        .nunique()
    )

    retention = df.groupby(["CohortMonth", "CohortIndex"])["CustomerID"].nunique()
    retention = retention.unstack(fill_value=0)
    retention = retention.div(cohort_sizes, axis=0)

    return retention.round(4)



def compute_rfm(df, reference_date=None):
    """
    Calcule Recency, Frequency et Monetary pour chaque client.
    """
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    
    if reference_date is None:
        reference_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
    
    rfm = df.groupby("CustomerID").agg({
        "InvoiceDate": lambda x: (reference_date - x.max()).days,
        "InvoiceNo": "nunique",
        "TotalPrice": "sum"
    })
    
    rfm.columns = ["Recency", "Frequency", "Monetary"]

    # Scores 1-5
    rfm["R"] = pd.qcut(rfm["Recency"], 5, labels=[5,4,3,2,1])
    rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1,2,3,4,5])
    rfm["M"] = pd.qcut(rfm["Monetary"], 5, labels=[1,2,3,4,5])

    rfm["RFM_Score"] = rfm[["R","F","M"]].astype(int).sum(axis=1)

    return rfm
