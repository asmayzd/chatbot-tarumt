import re
import sqlite3
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
        "insert", "update", "delete", "drop", "alter", "create",
        "replace", "truncate", "attach", "detach", "pragma",
        "vacuum", "reindex", "grant", "revoke",
    ]

    # Tables/views an analyst may query. `customers` is replaced by an
    # anonymised view: analysts need segments, not identities.
    ANALYST_TABLES = ["customers_anon", "products", "orders", "order_items"]

    # An admin may additionally read the nominative customer table.
    ADMIN_TABLES = ["customers", "products", "orders", "order_items"]

    # Views a `user` may query (created per session, already filtered).
    SCOPED_VIEWS = ["my_orders", "my_order_items"]

    # Columns carrying personal data. Never exposed below the admin role.
    PII_COLUMNS = ["customer_name"]

    def __init__(self, db_path: str = "data/superstore_bi.db",
                 model: str = "gemini-3.5-flash"):
        self.db_path = db_path
        self.model = model
        self.connection = None
        self.client = None
        self._scoped_for = None  # customer_id the views are currently built for

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def connect_database(self):
        """Open a connection to the persistent database (Streamlit-safe)."""
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._build_anon_view()
        return self

    def _build_anon_view(self):
        """Expose customer segments without the nominative column."""
        cursor = self.connection.cursor()
        cursor.execute("DROP VIEW IF EXISTS customers_anon")
        cursor.execute("""
            CREATE TEMP VIEW customers_anon AS
            SELECT customer_id, segment FROM customers
        """)
        self.connection.commit()

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
        """
        (Re)create views restricted to a single customer.

        Views are temporary and rebuilt whenever the customer changes, so one
        session can never read another customer's rows.
        """
        if self.connection is None:
            raise ValueError("Database not connected.")

        if self._scoped_for == customer_id:
            return  # already built for this customer

        cursor = self.connection.cursor()

        # Parameter binding is not allowed in CREATE VIEW, so the id is
        # validated against a strict pattern before being interpolated.
        if not re.fullmatch(r"[A-Za-z0-9\-_]{1,32}", customer_id or ""):
            raise ValueError("Invalid customer identifier.")

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
            SELECT oi.order_id, oi.product_id, oi.sales, oi.quantity,
                   oi.discount, oi.profit, oi.shipping_cost
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.customer_id = '{customer_id}'
        """)

        self.connection.commit()
        self._scoped_for = customer_id

    def _tables_for(self, role: str):
        if role == "user":
            return self.SCOPED_VIEWS
        if role == "admin":
            return self.ADMIN_TABLES
        return self.ANALYST_TABLES

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------
    def get_schema_description(self, role: str = "analyst") -> str:
        """Describe only the tables/views this role is allowed to query."""
        if self.connection is None:
            raise ValueError("Database not connected.")

        cursor = self.connection.cursor()
        lines = []

        for table in self._tables_for(role):
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            if not columns:
                continue

            cols = [f"{c[1]} ({c[2] or 'TEXT'})" for c in columns]
            lines.append(f"Table {table}: " + ", ".join(cols))

            cursor.execute(f"PRAGMA foreign_key_list({table})")
            for fk in cursor.fetchall():
                lines.append(f"  - {table}.{fk[3]} references {fk[2]}.{fk[4]}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Prompting
    # ------------------------------------------------------------------
    def _build_prompt(self, question: str, role: str) -> str:
        schema = self.get_schema_description(role)

        if role == "user":
            context = (
                "These views already contain ONLY the current customer's own "
                "orders. Never mention other customers. Do not add any filter "
                "on customer_id: the restriction is already applied."
            )
        else:
            context = (
                "Numeric measures (sales, profit, quantity, discount) live in "
                "order_items. Country, city, region, market and dates live in "
                "orders. Category and product_name live in products. Segment "
                "lives in customers_anon, which contains no customer names. "
                "Customer identities are confidential and must never be "
                "queried or returned. Join through order_id, product_id and "
                "customer_id when needed."
            )

        return f"""
You are an expert data analyst who writes SQLite queries.

Database schema (relational, use JOINs when the answer spans several tables):
{schema}

{context}

Rules:
1. Write ONE single valid SQLite SELECT query that answers the question.
2. Only use the tables and columns listed above. Never reference any other table.
3. Output ONLY the raw SQL query: no explanation, no comment, no markdown.
4. Never modify data: only SELECT statements are allowed.
5. Use LIMIT when the user asks for "top", "best" or "worst" results.

User question: "{question}"

SQL query:
""".strip()

    def _clean_sql(self, raw_sql: str) -> str:
        """Strip markdown fences, leading comments and trailing semicolons."""
        sql = raw_sql.strip()
        sql = re.sub(r"^```sql", "", sql, flags=re.IGNORECASE).strip()
        sql = re.sub(r"^```", "", sql).strip()
        sql = re.sub(r"```$", "", sql).strip()

        # Drop any leading "-- comment" lines the model may have added.
        lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
        sql = "\n".join(lines).strip()

        return sql.rstrip(";").strip()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    # Human-readable reasons, so the interface can explain *why* a query failed.
    REASON_READONLY = "readonly"
    REASON_SCOPE = "scope"
    REASON_PII = "pii"

    def check_sql(self, sql: str, role: str = "analyst"):
        """
        Validate a generated query.

        Returns (True, None) when the query is safe, otherwise (False, reason)
        where reason is one of REASON_READONLY / REASON_SCOPE / REASON_PII.
        """
        lowered = sql.lower().strip()

        # A read-only query starts with SELECT, or with a WITH clause (CTE)
        # that ultimately feeds a SELECT. Writes are caught below.
        if not (lowered.startswith("select") or lowered.startswith("with")):
            return False, self.REASON_READONLY

        if ";" in sql.strip().rstrip(";"):
            return False, self.REASON_READONLY

        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", lowered):
                return False, self.REASON_READONLY

        # Only an admin may read nominative customer data.
        if role != "admin":
            if re.search(r"\bcustomers\b", lowered):
                return False, self.REASON_PII
            for column in self.PII_COLUMNS:
                if re.search(rf"\b{column}\b", lowered):
                    return False, self.REASON_PII

        # Allowlist: a `user` may only read the views scoped to their own rows.
        # Anything not explicitly permitted is refused, so a table added to the
        # database later cannot silently become readable.
        if role == "user":
            referenced = re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", lowered)
            allowed = {v.lower() for v in self.SCOPED_VIEWS}
            if any(table not in allowed for table in referenced):
                return False, self.REASON_SCOPE

        return True, None

    def is_safe_sql(self, sql: str, role: str = "analyst") -> bool:
        """Backward-compatible boolean wrapper around check_sql()."""
        safe, _ = self.check_sql(sql, role)
        return safe

    def _denial_message(self, reason: str, role: str) -> str:
        """Explain the refusal in terms that match the user's role."""
        if reason == self.REASON_PII:
            return (
                "Access Denied: customer personal data is confidential. "
                "Your role can analyse aggregated figures (segments, regions, "
                "categories) but cannot access customer identities."
            )
        if reason == self.REASON_SCOPE:
            return (
                "Access Denied: you can only query your own orders. "
                "Company-wide data is restricted to analysts and administrators."
            )
        return (
            "Access Denied: the generated query was rejected because only "
            "read-only queries are allowed."
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
        if self.connection is None:
            raise ValueError("Database not connected.")
        return pd.read_sql_query(sql, self.connection)

    def ask(self, question: str, role: str = "analyst",
            customer_id: str = None) -> dict:
        """
        Full pipeline: scope -> SQL -> security check -> execution.

        For the `user` role a customer_id is mandatory: without it there is
        nothing to scope the views to, so the request is refused.
        """
        if role == "user":
            if not customer_id:
                return {
                    "question": question, "sql": None, "result": None,
                    "error": ("Access Denied: this session has no customer scope, "
                              "so no personal order data can be retrieved."),
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
Detect the language of the user question and reply in that same
language. Be concise and go straight to the data point. No filler.
""".strip()

        response = self.client.models.generate_content(
            model=self.model, contents=prompt,
        )
        return response.text.strip()