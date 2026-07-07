import re
import sqlite3
import pandas as pd


class SQLAgent:
    """
    Natural-language-to-SQL agent for the Superstore relational database.

    The agent connects to the persistent SQLite database (built from the
    schema.sql DDL), introspects the schema of the business tables and
    their foreign keys, then uses the Gemini LLM to translate a natural
    language question into a safe SELECT query (with JOINs when needed),
    validates it, executes it, and returns the result.
    """

    FORBIDDEN_KEYWORDS = [
        "insert", "update", "delete", "drop", "alter", "create",
        "replace", "truncate", "attach", "detach", "pragma",
        "vacuum", "reindex", "grant", "revoke",
    ]

    DEFAULT_TABLES = ["customers", "products", "orders", "order_items"]

    def __init__(self, db_path: str = "data/superstore_bi.db",
                 allowed_tables=None, model: str = "gemini-2.5-flash"):
        self.db_path = db_path
        self.allowed_tables = allowed_tables or self.DEFAULT_TABLES
        self.model = model
        self.connection = None
        self.client = None

    def connect_database(self):
        """Open a connection to the persistent database (Streamlit-safe)."""
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        return self

    def init_gemini(self):
        """Initialise the Gemini client (reads GEMINI_API_KEY from env)."""
        from google import genai
        self.client = genai.Client()
        return self

    def setup(self):
        """Convenience method: connect to the DB and init Gemini."""
        return self.connect_database().init_gemini()

    def get_schema_description(self) -> str:
        """Describe allowed tables, columns and foreign keys for the prompt."""
        if self.connection is None:
            raise ValueError("Database not connected. Call connect_database() first.")

        cursor = self.connection.cursor()
        lines = []

        for table in self.allowed_tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()

            if not columns:
                continue

            column_descriptions = [
                f"{col[1]} ({col[2] or 'TEXT'})" for col in columns
            ]
            lines.append(f"Table {table}: " + ", ".join(column_descriptions))

            cursor.execute(f"PRAGMA foreign_key_list({table})")
            for fk in cursor.fetchall():
                lines.append(f"  - {table}.{fk[3]} references {fk[2]}.{fk[4]}")

        return "\n".join(lines)

    def _build_prompt(self, question: str) -> str:
        schema = self.get_schema_description()

        return f"""
You are an expert data analyst who writes SQLite queries.

Database schema (relational, use JOINs when the answer spans several tables):
{schema}

Rules:
1. Write ONE single valid SQLite SELECT query that answers the question.
2. Only use the tables and columns listed above.
3. Numeric measures (sales, profit, quantity, discount) live in order_items.
   Country, city, region, market and dates live in orders.
   Category and product_name live in products. Segment lives in customers.
   Join through order_id and product_id / customer_id when needed.
4. Output ONLY the raw SQL query: no explanation, no comment, no markdown.
5. Never modify data: only SELECT statements are allowed.
6. Use LIMIT when the user asks for "top", "best" or "worst" results.

User question: "{question}"

SQL query:
""".strip()

    def _clean_sql(self, raw_sql: str) -> str:
        """Remove markdown fences and trailing semicolons."""
        sql = raw_sql.strip()
        sql = re.sub(r"^```sql", "", sql, flags=re.IGNORECASE).strip()
        sql = re.sub(r"^```", "", sql).strip()
        sql = re.sub(r"```$", "", sql).strip()
        return sql.rstrip(";").strip()

    def is_safe_sql(self, sql: str) -> bool:
        """Return True only for a single read-only SELECT statement."""
        lowered = sql.lower().strip()

        if not lowered.startswith("select"):
            return False

        if ";" in sql.strip().rstrip(";"):
            return False

        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", lowered):
                return False

        return True

    def generate_sql(self, question: str) -> str:
        """Ask Gemini to translate the question into a SQL query."""
        if self.client is None:
            raise ValueError("Gemini client not initialised. Call init_gemini() first.")

        prompt = self._build_prompt(question)

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return self._clean_sql(response.text)

    def run_sql(self, sql: str) -> pd.DataFrame:
        """Execute a SQL query and return the result as a DataFrame."""
        if self.connection is None:
            raise ValueError("Database not connected. Call connect_database() first.")

        return pd.read_sql_query(sql, self.connection)

    def ask(self, question: str) -> dict:
        """Full pipeline: question -> SQL -> security check -> execution."""
        sql = self.generate_sql(question)

        if not self.is_safe_sql(sql):
            return {
                "question": question,
                "sql": sql,
                "result": None,
                "error": (
                    "Generated query rejected for security reasons "
                    "(only read-only SELECT queries are allowed)."
                ),
            }

        try:
            result = self.run_sql(sql)
            error = None
        except Exception as exc:
            result = None
            error = f"SQL execution failed: {exc}"

        return {
            "question": question,
            "sql": sql,
            "result": result,
            "error": error,
        }

    def explain_result(self, question: str, result: pd.DataFrame) -> str:
        """Use Gemini to phrase the SQL result in natural language."""
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
            model=self.model,
            contents=prompt,
        )

        return response.text.strip()