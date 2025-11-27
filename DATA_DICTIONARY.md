# Dictionnaire de données — Online Retail II

| Variable            | Type        | Description                                                                 | Unités / Valeurs                           |
|---------------------|-------------|-----------------------------------------------------------------------------|---------------------------------------------|
| InvoiceNo           | string      | Identifiant unique de facture (préfixe "C" pour retour)                     | Alphanumérique                              |
| StockCode           | string      | Code article                                                                | Alphanumérique                              |
| Description         | string      | Description produit                                                          | Texte                                       |
| Quantity            | integer     | Quantité vendue (négatif si retour)                                         | Nombre d'unités                             |
| InvoiceDate         | datetime    | Date et heure de la transaction                                             | Timestamp                                   |
| UnitPrice           | float       | Prix unitaire du produit                                                    | Livre sterling (£)                          |
| CustomerID          | string      | Identifiant client (peut être manquant)                                     | Numérique                                   |
| Country             | string      | Pays du client                                                              | Texte                                       |
| is_return           | boolean     | Indique si la facture correspond à un retour                                | True / False                                |
| TotalPrice          | float       | Montant total de la ligne (Quantity * UnitPrice)                            | Livre sterling (£)                          |
| InvoiceMonth        | integer     | Mois de la transaction                                                      | 1-12                                        |
| InvoiceYear         | integer     | Année de la transaction                                                     | 2009-2011                                   |
| InvoiceYearMonth    | string      | Période agrégée année-mois                                                  | Format YYYY-MM                              |
| R_Score             | integer     | Score de récence (1 = ancien, 5 = récent)                                   | 1-5                                         |
| F_Score             | integer     | Score de fréquence (1 = faible, 5 = élevée)                                 | 1-5                                         |
| M_Score             | integer     | Score monétaire (1 = faible, 5 = élevé)                                     | 1-5                                         |
| RFM_Score           | string      | Combinaison des scores R, F, M                                              | Chaîne de trois chiffres (ex: 555)          |
| Segment             | string      | Segment marketing issu de la grille RFM                                     | Champions, Loyal, Potential Loyalists, etc. |
| Revenue             | float       | Revenu cumulé client                                                        | Livre sterling (£)                          |
| Orders              | integer     | Nombre de commandes distinctes                                              | Compte                                      |
| Units               | integer     | Volume total d'unités commandées                                            | Compte                                      |
| min                 | datetime    | Date de première commande                                                   | Timestamp                                   |
| max                 | datetime    | Date de dernière commande                                                   | Timestamp                                   |
| TenureDays          | integer     | Ancienneté client en jours                                                  | Jours                                       |
| AverageOrderValue   | float       | Panier moyen client                                                         | Livre sterling (£)                          |
| PurchaseFrequency   | float       | Fréquence d'achat mensuelle moyenne                                         | Commandes / mois                            |
| CLV                 | float       | Customer Lifetime Value annuel estimé                                      | Livre sterling (£)                          |
| TenureMonths        | float       | Ancienneté client convertie en mois                                         | Mois                                        |
