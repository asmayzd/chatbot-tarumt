import re
import sqlite3
import pandas as pd


class SQLAgent:
    """
    Natural-language-to-SQL agent for the Superstore dataset.

    The agent loads a cleaned DataFrame into an in-memory SQLite
    database, uses the Gemini LLM to translate a natural language
    question into a safe SELECT query, validates it, executes it,
    and returns the result.
    """

    FORBIDDEN_KEYWORDS = [
        "insert", "update", "delete", "drop", "alter", "create",
        "replace", "truncate", "attach", "detach", "pragma",
        "vacuum", "reindex", "grant", "revoke",
    ]

    def __init__(self, df: pd.DataFrame, table_name: str = "superstore",
                 model: str = "gemini-2.5-flash"):
        self.df = df.copy()
        self.table_name = table_name
        self.model = model
        self.connection = None
        self.client = None

    def build_database(self):
        """Load the DataFrame into an in-memory SQLite database."""
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.df.to_sql(
            self.table_name,
            self.connection,
            if_exists="replace",
            index=False,
        )
        return self

    def init_gemini(self):
        """Initialise the Gemini client (reads GEMINI_API_KEY from env)."""
        from google import genai
        self.client = genai.Client()
        return self

    def setup(self):
        """Convenience method: build the database and init Gemini."""
        return self.build_database().init_gemini()

    def get_schema_description(self) -> str:
        """Build a textual description of the table schema for the prompt."""
        lines = [f"Table name: {self.table_name}", "Columns:"]

        for column in self.df.columns:
            dtype = str(self.df[column].dtype)
            sample_values = self.df[column].dropna().unique()[:3]
            samples = ", ".join(str(value) for value in sample_values)
            lines.append(f"- {column} ({dtype}) e.g. {samples}")

        return "\n".join(lines)

    def _build_prompt(self, question: str) -> str:
        schema = self.get_schema_description()

        return f"""
You are an expert data analyst who writes SQLite queries.

{schema}

Rules:
1. Write ONE single valid SQLite SELECT query that answers the question.
2. Only use the table and columns listed above.
3. Output ONLY the raw SQL query: no explanation, no comment, no markdown.
4. Never modify data: only SELECT statements are allowed.
5. Use LIMIT when the user asks for "top", "best" or "worst" results.

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

        # Block stacked queries (only one statement allowed)
        if ";" in sql.strip().rstrip(";"):
            return False

        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", lowered):
                return False

        return True

    def generate_sql(self, question: str) -> str:
        """Ask Gemini to translate the question into a SQL query."""
        if self.client is None:
            raise ValueError(
                "Gemini client not initialised. Call init_gemini() first."
            )

        prompt = self._build_prompt(question)

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return self._clean_sql(response.text)

    def run_sql(self, sql: str) -> pd.DataFrame:
        """Execute a SQL query and return the result as a DataFrame."""
        if self.connection is None:
            raise ValueError(
                "Database not built. Call build_database() first."
            )

        return pd.read_sql_query(sql, self.connection)

    def ask(self, question: str) -> dict:
        """
        Full pipeline: question -> SQL -> security check -> execution.
        Returns a dictionary with the generated SQL and the result.
        """
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
