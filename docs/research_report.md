# Rapport de recherche

**Sujet :** Chatbot intelligent sécurisé pour l'analyse de données e-commerce
et l'aide à la décision.

## 1. Contexte et objectif

Les entreprises e-commerce produisent de grandes quantités de données de vente.
Les décideurs métier ont besoin d'accéder rapidement à des indicateurs (CA,
produits populaires, tendances) sans passer par un analyste à chaque question.
L'objectif est de construire un **assistant conversationnel** qui répond en
langage naturel à des questions métier, tout en **garantissant la sécurité**
des données (accès par rôle, protection contre les manipulations).

## 2. Problématique

Comment concevoir un chatbot qui soit à la fois :
- **utile** : répond correctement aux questions métier à partir de vraies données ;
- **fiable** : n'invente pas de chiffres, indique ses sources ;
- **sécurisé** : résiste aux tentatives de prompt injection et d'exfiltration,
  et respecte les droits d'accès de chaque rôle.

## 3. Données

Un jeu de données e-commerce synthétique de ~3 155 commandes sur l'année 2025
a été généré, avec saisonnalité (pic en novembre/décembre), 17 produits sur 5
catégories, 372 clients et 7 régions. Une version « brute » contient des
défauts réalistes (doublons, quantités négatives, valeurs manquantes, montants
aberrants) ; le nettoyage produit `dataset_clean.csv`. Douze anomalies
résiduelles sont conservées volontairement pour tester la détection.

## 4. Méthode

### 4.1 Analyse BI
Les KPI (CA total, panier moyen, produits populaires, meilleur mois, clients
inactifs, anomalies) sont calculés avec pandas et exposés par `get_kpi()`. Les
anomalies sont détectées via le **prix unitaire effectif** (montant / quantité)
comparé au prix catalogue, ce qui isole les incohérences sans pénaliser les
grosses quantités.

### 4.2 Moteur conversationnel
Le chatbot détecte l'intention de la question par un système de règles à base
de mots-clés normalisés (minuscules, sans accents). Cinq intentions sont
gérées : KPI, tendance, anomalie, documentaire, général. Selon l'intention, la
requête est routée vers les KPI ou vers un pipeline **RAG** documentaire.

### 4.3 RAG documentaire
La FAQ est découpée en passages, vectorisée en TF-IDF ; la question est comparée
par similarité cosinus pour retrouver le passage le plus pertinent. Cette
approche légère évite les dépendances lourdes tout en respectant le principe du
RAG (elle est remplaçable par une base vectorielle type FAISS/ChromaDB).

### 4.4 Sécurité
Trois rôles (admin, analyste, utilisateur) et une matrice d'accès. Le filtre
`check_security()` détecte par motifs : prompt injection, injection SQL,
exfiltration de secrets, accès aux données personnelles. Toutes les interactions
sont journalisées.

## 5. Résultats

- **Détection d'intention** : 100 % de bonnes classifications sur un jeu de test
  de 20 questions (`evaluation_results.csv`). Ce score élevé s'explique par le
  périmètre restreint et le vocabulaire métier bien couvert.
- **Sécurité** : 18/18 scénarios d'attaque correctement traités
  (`attack_tests.csv`), y compris les variantes avec accents.
- **Tests unitaires** : 23/23 passent.

## 6. Limites

- La détection par règles est efficace sur le domaine couvert mais fragile face
  à des formulations très éloignées ; un classifieur ML serait plus robuste.
- Le RAG TF-IDF ne capture pas la sémantique fine (synonymes, paraphrases) ;
  des embeddings amélioreraient le rappel.
- Le filtre de sécurité par regex peut être contourné par des formulations
  inédites ; un modèle de détection dédié serait un complément utile.

## 7. Perspectives

- Brancher un LLM (via le `PROMPT_SYSTEME` déjà prévu) pour des réponses plus
  naturelles, en gardant le RAG comme fournisseur de contexte factuel.
- Remplacer le stockage CSV par une base SQL et FAISS/ChromaDB pour le RAG.
- Ajouter authentification forte (JWT/bcrypt), rate-limiting et chiffrement des
  logs.
- Enrichir le dashboard avec des prévisions de ventes (séries temporelles).

## 8. Conclusion

Le projet démontre qu'une architecture modulaire à contrats clairs permet de
combiner analyse BI, IA conversationnelle et sécurité dans un même produit, et
de faire évoluer chaque brique indépendamment. La version MVP est fonctionnelle
de bout en bout : login, question, filtre de sécurité, réponse fondée sur les
données, journalisation et dashboard.
