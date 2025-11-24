
---

# 🎉 **README.md – Projet ECE DataViz 2025**

### **Analyse Cohortes • Segmentation RFM • CLV • Simulation Marketing**


**Membres : Benjamin • Paul • Gilles • Nicolas • Antoine • Arthur**

---

# 📌 1. Contexte du projet

Ce projet est réalisé dans le cadre du cours **Dataviz & Data Storytelling** à l’ECE.
Il consiste à développer une application interactive permettant d’analyser le comportement client et de produire des recommandations marketing basées sur :

* l’analyse des **cohortes d’acquisition**,
* la segmentation **RFM**,
* l’estimation de la **Customer Lifetime Value (CLV)**,
* la simulation de **scénarios business**,
* et l’export de données actionnables.

Le tout à partir du dataset **Online Retail II (UCI)** contenant ~1M de transactions e-commerce (2009–2011).

---

# 🎯 2. Objectifs analytiques

### **Cohortes**

* Rétention M+1, M+2…
* Détection des cohortes qui décrochent
* Analyse du revenu par âge de cohorte

### **Segmentation RFM**

* Calcul Recency–Frequency–Monetary
* Création de segments actionnables
* Comparaison des segments

### **CLV**

* Approche empirique (cohortes)
* Modèle paramétrique (r, d)
* Comparaison des méthodes

### **Scénarios**

* Simulation % rétention
* Simulation % remises
* Simulation marge
* Effet sur CA / CLV / rétention

### **Exports**

* CSV “liste activable”
* Graphiques PNG

---

# 🖥️ 3. Contenu de l’application

### **1. KPIs**

Affichage des indicateurs clés (clients actifs, CA, RFM, CLV baseline, rétention, etc.).
Chaque KPI inclut une **définition + unité + exemple**.

### **2. Cohortes**

Heatmap, évolutions de rétention, focus cohortes, filtres.

### **3. RFM**

Calcul des scores, labels, tableau des segments.

### **4. CLV & Scénarios**

Estimation, sliders de simulation, graphiques before/after.

### **5. Exports**

CSV & PNG.

---

# 📦 4. Données

Dataset : **Online Retail II – UCI**
Période : 2009–2011
Colonnes principales : CustomerID, InvoiceDate, Quantity, UnitPrice, Country…

Nettoyages :

* exclusion des factures annulées
* quantités/prix négatifs
* TotalPrice
* gestion valeurs manquantes

---

# 🧑‍💻 5. Membres du groupe & responsabilités

| Membre       | Tâches principales                   |
| ------------ | ------------------------------------ |
| **Benjamin** | Cohortes & Rétention                 |
| **Paul**     | Segmentation RFM                     |
| **Gilles**   | Notebook d’exploration visuelle      |
| **Nicolas**  | Préparation & nettoyage des données  |
| **Antoine**  | Estimation CLV (empirique + formule) |
| **Arthur**   | Application Streamlit & Interface    |


---

# 🚀 6. Instructions

### Installation

```bash
pip install -r requirements.txt
```

### Lancement de l’application

```bash
streamlit run app.py
```

vec badges ? 💎
