# 📘 Projet ECE DataViz 2025

**Cohortes · RFM · CLV · Scénarios Marketing**

## 🎯 Présentation

Ce projet consiste à développer une **application d’aide à la décision marketing** basée sur :

* l’analyse des **cohortes d’acquisition**,
* la segmentation **RFM**,
* l’estimation de la **Customer Lifetime Value (CLV)**,
* et la simulation de **scénarios business** (marge, remise, rétention…).

**Données utilisées :** Online Retail II (UCI) — 1,07M transactions e-commerce UK entre *2009 et 2011*.

---

## 🧪 Partie 1 — Notebook d’exploration

Objectif : obtenir une compréhension solide du dataset avant la construction de l’application.

Le notebook devra inclure :

* Une fiche synthétique des données + dictionnaire des variables
* Analyse qualité : manquants, doublons, retours ("C"), outliers
* Visualisations clés (6–8) : distributions, saisonnalité, pays, premiers signaux cohortes & RFM
* Interprétations claires de chaque graphique
* Questions d’analyse pour cadrer l’app : cohorte qui décrochent, segments à forte valeur, effet des retours…

---

## 💻 Partie 2 — Application Streamlit

L’application doit permettre à l’équipe marketing de :

### 🔍 Diagnostiquer

* Heatmap de rétention par cohortes
* Courbes de revenu par âge de cohorte
* Segments RFM (taille, CA, marge, priorités d’action)

### 📈 Simuler

* Variation de rétention (r)
* Variation de marge / remise
* Taux d’actualisation (d)
* Application globale ou par segment RFM

Objectif : mesurer instantanément l’impact sur **CLV**, **CA** et **rétention**.

### 📤 Exporter

* CSV des listes activables (CustomerID + segment)
* PNG des visualisations
  → pour faciliter le passage à l’action (CRM, campagnes…).

---

## 📐 KPIs — Definitions attendues

Chaque KPI devra afficher une aide intégrée :

* CLV moyenne
* Rétention à t (ex : M+3)
* Score RFM
* CLV empirique vs formule
  Objectif : rendre l’app explicite et compréhensible par un utilisateur non technique.

---

## 🎨 Lignes directrices recommandées

* Toujours afficher les filtres actifs
* Donner les effectifs (n)
* Une idée par graphique
* Labels lisibles, contraste suffisant
* Gestion explicite des valeurs manquantes/outliers
* Comparaisons baseline vs scénario clairement indiquées
