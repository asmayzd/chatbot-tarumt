import re
import configparser
import os
import psycopg2
import pandas as pd


class SQLAgent:
    """
    Natural-language-to-SQL agent for the Superstore relational database.

    Security model
    --------------
    Analysts and admins query the base tables directly.

    A `user` never does. For each session a set of *scoped views* is created,
    pre-filtered on that customer's own `customer_id`. The agent is only ever
    shown those views, and any generated query that references a base table is
    rejected. Row-level security is therefore enforced by the database, not by
    trusting the language model to add a WHERE clause.
    """

    FORBIDDEN_KEYWORDS = [
        "insert", "delete", "drop", "alter", "create",
        "replace", "truncate", "attach", "detach", "pragma",
        "vacuum", "reindex", "grant", "revoke",
    ]

    ANALYST_TABLES = ["customers_anon", "products", "orders", "order_items"]
    ADMIN_TABLES = ["customers", "products", "orders", "order_items", "chat_messages"]
    SCOPED_VIEWS = ["my_orders", "my_order_items"]
    PII_COLUMNS = ["customer_name"]

    def __init__(self, db_path: str = "data/superstore_bi.db",
                 model: str = "gemini-3.1-flash-lite"):
        self.db_path = db_path
        self.model = model
        self.connection = None
        self.client = None
        self._scoped_for = None

    # ------------------------------------------------------------------
    # Setup & Connection Management (Auto-Reconnect)
    # ------------------------------------------------------------------
    def get_connection(self):
        """Vérifie et rétablit la connexion PostgreSQL si elle est fermée."""
        if self.connection is None or getattr(self.connection, 'closed', 1) != 0:
            print("🔄 Reconnexion à PostgreSQL/Supabase en cours...")
            self.connect_database()
        return self.connection

    def connect_database(self):
        """Se connecte directement à PostgreSQL / Supabase."""
        try:
            config = configparser.ConfigParser()
            config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config.ini"))
            if not os.path.exists(config_path):
                config_path = "config.ini"
            config.read(config_path)

            db_host = config.get("postgresql", "host", fallback="127.0.0.1")
            db_port = config.get("postgresql", "port", fallback="5432")
            db_name = config.get("postgresql", "database", fallback="postgres")
            db_user = config.get("postgresql", "user", fallback="postgres")
            db_pass = config.get("postgresql", "password", fallback="postgres")

            self.connection = psycopg2.connect(
                host=db_host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_pass
            )
            print("✅ SQLAgent connecté à PostgreSQL/Supabase avec succès !")
            return self
        except Exception as e:
            print(f"❌ Erreur connexion PostgreSQL SQLAgent: {e}")
            raise e

    def _build_anon_view(self):
        """Expose customer segments without the nominative column."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DROP VIEW IF EXISTS customers_anon")
            cursor.execute("""
                CREATE TEMP VIEW customers_anon AS
                SELECT customer_id, segment FROM customers
            """)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    def init_gemini(self):
        """Initialise the Gemini client (reads GEMINI_API_KEY from env)."""
        from google import genai
        self.client = genai.Client()
        return self

    def setup(self):
        return self.connect_database().init_gemini()

    # ------------------------------------------------------------------
    # Row-level security
    # ------------------------------------------------------------------
    def build_scoped_views(self, customer_id: str):
        """(Re)create views restricted to a single customer."""
        conn = self.get_connection()

        if self._scoped_for == customer_id:
            return

        if not re.fullmatch(r"[A-Za-z0-9\-_]{1,32}", customer_id or ""):
            raise ValueError("Invalid customer identifier.")

        cursor = conn.cursor()
        try:
            cursor.execute("DROP VIEW IF EXISTS my_order_items")
            cursor.execute("DROP VIEW IF EXISTS my_orders")

            cursor.execute(f"""
                CREATE TEMP VIEW my_orders AS
                SELECT order_id, order_date, ship_date, ship_mode,
                       market, region, country, city, state
                FROM orders
                WHERE customer_id = '{customer_id}'
            """)

            cursor.execute(f"""
                CREATE TEMP VIEW my_order_items AS
                SELECT oi.order_id, oi.product_id, p.product_name, oi.sales, oi.quantity,
                       oi.discount, oi.profit, oi.shipping_cost
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                LEFT JOIN products p ON oi.product_id = p.product_id
                WHERE o.customer_id = '{customer_id}'
            """)
            
            conn.commit()
            self._scoped_for = customer_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    def _tables_for(self, role: str):
        if role == "user":
            return self.SCOPED_VIEWS
        if role == "admin":
            return self.ADMIN_TABLES
        return self.ANALYST_TABLES

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------
    def get_schema_description(self, role: str = "admin") -> str:
        """Retourne la description des tables adaptées à PostgreSQL."""
        conn = self.get_connection()
        schema_desc = ""
        
        if role == "user":
            tables = ["my_orders", "my_order_items"]
        elif role == "admin":
            tables = ["customers", "orders", "order_items", "products", "chat_messages"]
        else:
            tables = ["customers_anon", "orders", "order_items", "products"]
            
        cursor = conn.cursor()

        for table in tables:
            schema_desc += f"\nTable: {table}\nColumns:\n"
            try:
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s;
                """, (table,))
                columns = cursor.fetchall()

                if columns:
                    for col in columns:
                        schema_desc += f" - {col[0]} ({col[1]})\n"
                else:
                    cursor.execute(f"PRAGMA table_info({table})")
                    for col in cursor.fetchall():
                        schema_desc += f" - {col[1]} ({col[2]})\n"
            except Exception:
                conn.rollback()

        cursor.close()
        return schema_desc

    # ------------------------------------------------------------------
    # Prompting
    # ------------------------------------------------------------------
    def _build_prompt(self, question: str, role: str) -> str:
        schema = self.get_schema_description(role)

        if role == "user":
            context = (
                "You are querying for the logged-in customer. "
                "You MUST query strictly from 'my_orders' or 'my_order_items'. "
                "Do NOT reference 'orders', 'order_items' or 'customers' base tables. "
                "The restriction on customer_id is ALREADY applied inside the view."
            )
        elif role == "admin":
            context = (
                "As an admin, you can read and UPDATE tables when requested "
                "(e.g., updating customer names, order details). "
                "For questions about common or most asked questions, query column 'message' from 'chat_messages' WHERE sender = 'user'. "
                "Join through order_id, product_id and customer_id when needed."
            )
        else:
            context = (
                "CRITICAL COLUMN RULES:\n"
                "- Total sales must be calculated using SUM(oi.sales) directly.\n"
                "- NEVER invent a column named 'price'. There is no 'price' column in order_items.\n"
                "- Country is in 'orders.country'.\n"
                "- Always use GROUP BY when using aggregate functions like SUM()."
            )

        return f"""
You are an expert data analyst and database administrator.

Database schema:
{schema}

{context}

Rules:
1. Write ONE single valid SQL query (SELECT or UPDATE) that answers/performs the question.
2. Only use the tables and columns listed above. Never invent non-existent columns like 'price'.
3. Output ONLY the raw SQL query: no explanation, no comment, no markdown.

User question: "{question}"

SQL query:
""".strip()

    def _clean_sql(self, raw_sql: str) -> str:
        """Strip markdown fences, leading comments and trailing semicolons."""
        sql = raw_sql.strip()
        sql = re.sub(r"^```sql", "", sql, flags=re.IGNORECASE).strip()
        sql = re.sub(r"^```", "", sql).strip()
        sql = re.sub(r"```$", "", sql).strip()

        lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
        sql = "\n".join(lines).strip()

        return sql.rstrip(";").strip()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    REASON_READONLY = "readonly"
    REASON_SCOPE = "scope"
    REASON_PII = "pii"
    REASON_DATE_UPDATE = "date_update"

    def check_sql(self, sql: str, role: str = "analyst"):
        """Validate a generated query."""
        lowered = sql.lower().strip()

        is_select = lowered.startswith("select") or lowered.startswith("with")
        is_update = lowered.startswith("update") and role == "admin"

        if not (is_select or is_update):
            return False, self.REASON_READONLY

        if ";" in sql.strip().rstrip(";"):
            return False, self.REASON_READONLY

        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", lowered):
                return False, self.REASON_READONLY

        if role != "admin":
            if re.search(r"\bcustomers\b", lowered):
                return False, self.REASON_PII
            for column in self.PII_COLUMNS:
                if re.search(rf"\b{column}\b", lowered):
                    return False, self.REASON_PII

        if role == "user":
            referenced = re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", lowered)
            allowed = {v.lower() for v in self.SCOPED_VIEWS}
            if any(table not in allowed for table in referenced):
                return False, self.REASON_SCOPE

        return True, None

    def is_safe_sql(self, sql: str, role: str = "analyst") -> bool:
        safe, _ = self.check_sql(sql, role)
        return safe

    def _denial_message(self, reason: str, role: str) -> str:
        if reason == self.REASON_PII:
            return (
                "Access Denied: customer personal data is confidential. "
                "Your role can analyse aggregated figures but cannot access customer identities."
            )
        if reason == self.REASON_SCOPE:
            return (
                "Access Denied: you can only query your own orders."
            )
        return (
            "Access Denied: the generated query was rejected because "
            "this operation is not allowed for your role."
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def generate_sql(self, question: str, role: str = "analyst") -> str:
        if self.client is None:
            raise ValueError("Gemini client not initialised.")

        response = self.client.models.generate_content(
            model=self.model,
            contents=self._build_prompt(question, role),
        )
        return self._clean_sql(response.text)

    def run_sql(self, sql: str) -> pd.DataFrame:
        """Exécute les SELECT ainsi que les UPDATE avec gestion automatique du COMMIT/ROLLBACK."""
        conn = self.get_connection()
        lowered = sql.lower().strip()

        try:
            if lowered.startswith("update"):
                cursor = conn.cursor()
                cursor.execute(sql)
                conn.commit()
                rows_affected = cursor.rowcount
                cursor.close()
                return pd.DataFrame([{"status": "success", "message": f"Successfully updated {rows_affected} row(s)."}])
            else:
                df = pd.read_sql_query(sql, conn)
                return df
        except Exception as e:
            # Nettoie la transaction bloquée en cas d'erreur
            conn.rollback()
            raise e

    def ask(self, question: str, role: str = "analyst",
            customer_id: str = None) -> dict:
        """Full pipeline: scope -> SQL -> security check -> execution."""
        if role == "user":
            if not customer_id:
                return {
                    "question": question, "sql": None, "result": None,
                    "error": ("Access Denied: this session has no customer scope."),
                }
            self.build_scoped_views(customer_id)

        sql = self.generate_sql(question, role)

        safe, reason = self.check_sql(sql, role)
        if not safe:
            return {
                "question": question,
                "sql": sql,
                "result": None,
                "error": self._denial_message(reason, role),
            }

        try:
            result = self.run_sql(sql)
            error = None
        except Exception as exc:
            # Réinitialise la connexion PostgreSQL si elle a planté
            try:
                self.get_connection().rollback()
            except Exception:
                pass

            if "closed" in str(exc).lower() or "terminated" in str(exc).lower():
                try:
                    self.connection = None
                    result = self.run_sql(sql)
                    error = None
                except Exception as retry_exc:
                    result = None
                    error = f"SQL execution failed: {retry_exc}"
            else:
                result = None
                error = f"SQL execution failed: {exc}"

        return {"question": question, "sql": sql, "result": result, "error": error}

    def explain_result(self, question: str, result: pd.DataFrame) -> str:
        if self.client is None:
            raise ValueError("Gemini client not initialised.")

        preview = result.head(20).to_string(index=False)

        prompt = f"""
The user asked: "{question}"

Here is the SQL query result:
{preview}

Write a short, direct answer to the question based on this result.
Detect the language of the user question and reply in that same language.

STRICT FORMATTING RULES:
- Never use markdown syntax or asterisks (NO **, NO *, NO #, NO _).
- Return plain text ONLY.
- If listing multiple items, put EACH item on a new line starting with a number (e.g. 1. Item A \n 2. Item B).
""".strip()

        response = self.client.models.generate_content(
            model=self.model, contents=prompt,
        )
        return response.text.replace("*", "").strip()