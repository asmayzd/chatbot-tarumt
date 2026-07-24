import { ref, computed } from "vue";

// État partagé : un seul `lang` réactif pour toute l'application,
// quelle que soit la vue (login, chat, BI, sécurité).
export const lang = ref(localStorage.getItem("lang") || "en");

export function setLang(l) {
  if (l !== "en" && l !== "fr") return;
  lang.value = l;
  localStorage.setItem("lang", l);
}

const TRANSLATIONS = {
  en: {
    login: {
      title: "TARUMT System",
      subtitle: "Log in to access the assistant and BI dashboard.",
      userLabel: "Customer ID / Username",
      userPlaceholder: "e.g. analyst_tarumt",
      passwordLabel: "Password",
      connecting: "Connecting…",
      signIn: "Sign in",
    },
    chat: {
      biAnalytics: "BI Analytics", backToChat: "Back to chat", cybersecurity: "Cybersecurity",
      granted: "Granted", restricted: "Restricted", newChat: "+ New chat",
      noSessions: "No saved conversations yet.", logout: "Log out",
      heroTitle: "TARUMT Smart Assistant",
      heroDesc: "Ask about sales, profits and delivery times in natural language.",
      connected: "Connected", totalSales: "Total Sales", totalProfit: "Total Profit",
      anomalies: "Anomalies", biRestricted: "The BI dashboard is reserved for analyst / admin roles.",
      sqlUsed: "SQL query used", inputPlaceholder: "Type your question…", send: "Send",
      welcome: "Hello! Ask me about your data.",
    },
    bi: {
      title: "BI Analytics",
      totalSales: "Total Sales", totalProfit: "Total Profit", totalQuantity: "Total Quantity",
      avgDiscount: "Avg Discount", avgMargin: "Avg Profit Margin", avgShipping: "Avg Shipping Delay",
      salesByCountry: "Sales by country (top 10)", salesByMarket: "Sales by market",
      topProducts: "Top products by sales", profitByCategory: "Profit by category",
      bestWorstProducts: "Best & worst products by profit", anomaliesDetected: "Anomalies detected",
      leastProfitable: "Least profitable products", lowestMargin: "Lowest profit-margin countries",
      profit: "Profit", loss: "Loss", noData: "No data.",
      highSalesNegProfit: "High sales, negative profit", highDiscountNegProfit: "High discount, negative profit",
      longShipping: "Long shipping delays", unusualSales: "Unusual sales values",
    },
    security: {
      title: "Cybersecurity",
      events24h: "Events (24h)", failedLogins24h: "Failed logins (24h)",
      attacks24h: "Attacks blocked (24h)", bannedAccounts: "Banned accounts",
      chartTitle: "Attacks & failed logins — last 14 days",
      attacksBlocked: "Attacks blocked", failedLogins: "Failed logins",
      recentEvents: "Recent security events", noEvents: "No events found.",
      allStatuses: "All statuses", attacksFilter: "Attacks (blocked / critical)",
      failedFilter: "Failed logins", successFilter: "Success",
      time: "Time", user: "User", role: "Role", action: "Action", status: "Status", details: "Details",
    },
    common: { loading: "Loading…", refresh: "Refresh" },
  },
  fr: {
    login: {
      title: "TARUMT System",
      subtitle: "Connectez-vous pour accéder à l'assistant et au tableau de bord BI.",
      userLabel: "Identifiant client / Nom d'utilisateur",
      userPlaceholder: "ex. analyst_tarumt",
      passwordLabel: "Mot de passe",
      connecting: "Connexion…",
      signIn: "Se connecter",
    },
    chat: {
      biAnalytics: "BI Analytics", backToChat: "Retour au chat", cybersecurity: "Cybersécurité",
      granted: "Autorisé", restricted: "Restreint", newChat: "+ Nouvelle conversation",
      noSessions: "Aucune conversation enregistrée.", logout: "Se déconnecter",
      heroTitle: "Assistant Intelligent TARUMT",
      heroDesc: "Posez vos questions sur les ventes, les profits et les délais de livraison en langage naturel.",
      connected: "Connecté", totalSales: "Ventes totales", totalProfit: "Profit total",
      anomalies: "Anomalies", biRestricted: "Le tableau de bord BI est réservé aux rôles analyst / admin.",
      sqlUsed: "Requête SQL utilisée", inputPlaceholder: "Posez votre question…", send: "Envoyer",
      welcome: "Bonjour ! Posez-moi vos questions sur vos données.",
    },
    bi: {
      title: "BI Analytics",
      totalSales: "Ventes totales", totalProfit: "Profit total", totalQuantity: "Quantité totale",
      avgDiscount: "Remise moyenne", avgMargin: "Marge moyenne", avgShipping: "Délai de livraison moyen",
      salesByCountry: "Ventes par pays (top 10)", salesByMarket: "Ventes par marché",
      topProducts: "Meilleurs produits par ventes", profitByCategory: "Profit par catégorie",
      bestWorstProducts: "Meilleurs & pires produits par profit", anomaliesDetected: "Anomalies détectées",
      leastProfitable: "Produits les moins rentables", lowestMargin: "Pays à plus faible marge",
      profit: "Profit", loss: "Perte", noData: "Aucune donnée.",
      highSalesNegProfit: "Ventes élevées, profit négatif", highDiscountNegProfit: "Remise élevée, profit négatif",
      longShipping: "Délais de livraison longs", unusualSales: "Valeurs de vente inhabituelles",
    },
    security: {
      title: "Cybersécurité",
      events24h: "Événements (24h)", failedLogins24h: "Connexions échouées (24h)",
      attacks24h: "Attaques bloquées (24h)", bannedAccounts: "Comptes bannis",
      chartTitle: "Attaques & connexions échouées — 14 derniers jours",
      attacksBlocked: "Attaques bloquées", failedLogins: "Connexions échouées",
      recentEvents: "Événements de sécurité récents", noEvents: "Aucun événement trouvé.",
      allStatuses: "Tous les statuts", attacksFilter: "Attaques (bloquées / critiques)",
      failedFilter: "Connexions échouées", successFilter: "Succès",
      time: "Heure", user: "Utilisateur", role: "Rôle", action: "Action", status: "Statut", details: "Détails",
    },
    common: { loading: "Chargement…", refresh: "Actualiser" },
  },
};

export const t = computed(() => TRANSLATIONS[lang.value]);
