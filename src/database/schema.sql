-- 1. Table des Clients (Élimine la répétition des infos clients par commande)
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    segment TEXT NOT NULL
);

-- 2. Table des Produits (Élimine la répétition des noms et catégories de produits)
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    sub_category TEXT NOT NULL
);

-- 3. Table des Commandes (Contient les métadonnées globales de la commande)
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_date DATE NOT NULL,
    ship_date DATE NOT NULL,
    ship_mode TEXT NOT NULL,
    market TEXT NOT NULL,
    region TEXT NOT NULL,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- 4. Table de Détail des Lignes de Commande (Liaison N:N entre Commandes et Produits)
CREATE TABLE IF NOT EXISTS order_items (
    item_id SERIAL PRIMARY KEY,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    sales REAL NOT NULL,
    quantity INTEGER NOT NULL,
    discount REAL NOT NULL,
    profit REAL NOT NULL,
    shipping_cost REAL NOT NULL,
    order_priority TEXT NOT NULL,
    shipping_delay_days INTEGER NULL,
    profit_margin REAL NULL,
    chatbot_context TEXT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- 5. Table d'Authentification (comptes admin/analyst/user, séparée des données
-- métier). Remplace les identifiants codés en dur dans le code applicatif :
-- seul le hash bcrypt du mot de passe est stocké ici.
CREATE TABLE IF NOT EXISTS app_users (
    user_id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'analyst', 'user')),
    display_name TEXT NOT NULL,
    customer_id TEXT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_app_users_customer ON app_users(customer_id);

-- 6. Table des Sessions de Chat
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id SERIAL PRIMARY KEY,
    student_id TEXT NOT NULL,
    session_name TEXT NOT NULL DEFAULT 'Superstore Analysis',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Historique de chat : rattachement à un compte réel de app_users plutôt
-- qu'à un simple TEXT libre non vérifié (student_id, conservé pour l'existant).
ALTER TABLE chat_sessions ALTER COLUMN student_id DROP NOT NULL;
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES app_users(user_id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions(user_id);

-- 7. Table Dédiée à l'Historique des Messages
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);

-- Index pour accélérer les requêtes SQL de Besma et l'historique du Chat
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);


-- Création de la table intermédiaire pour la relation Many-to-Many
CREATE TABLE IF NOT EXISTS customer_messages (
    customer_id VARCHAR(50),
    message_id INT,
    PRIMARY KEY (customer_id, message_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES chat_messages(message_id) ON DELETE CASCADE
);

-- 8. Journal structuré des événements de sécurité (alimente le dashboard
-- cybersécurité de l'admin). Miroir de logs/security_audit.log mais
-- interrogeable en SQL (KPIs, historique des connexions, attaques bloquées).
CREATE TABLE IF NOT EXISTS security_events (
    event_id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_security_events_created ON security_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_status ON security_events(status);
CREATE INDEX IF NOT EXISTS idx_security_events_action ON security_events(action);