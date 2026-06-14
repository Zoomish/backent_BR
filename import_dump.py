import re
import sys
from io import StringIO

import psycopg2

DATABASE_URL = sys.argv[1] if len(sys.argv) > 1 else None
DUMP_PATH = sys.argv[2] if len(sys.argv) > 2 else None

if not DATABASE_URL or not DUMP_PATH:
    raise SystemExit("Usage: python import_dump.py <DATABASE_URL> <dump.sql>")


def read_dump(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def split_sql_statements(sql_text):
    statements = []
    current = []
    in_dollar = False
    in_copy = False

    for line in sql_text.splitlines(keepends=True):
        stripped = line.strip()

        if stripped.startswith("\\restrict") or stripped.startswith("\\unrestrict"):
            continue

        if line.startswith("COPY "):
            in_copy = True
            continue

        if in_copy:
            if stripped == "\\.":
                in_copy = False
            continue

        if stripped.startswith("\\"):
            continue

        if "$$" in line:
            if line.count("$$") % 2 == 1:
                in_dollar = not in_dollar

        current.append(line)

        if not in_dollar and line.rstrip().endswith(";"):
            statement = "".join(current).strip()
            if statement and re.search(r"\b(CREATE|ALTER|SELECT|INSERT|DROP|COMMENT)\b", statement, re.I):
                statements.append(statement)
            current = []

    tail = "".join(current).strip()
    if tail and re.search(r"\b(CREATE|ALTER|SELECT|INSERT|DROP|COMMENT)\b", tail, re.I):
        statements.append(tail)

    return statements


def import_copy_blocks(connection, dump_text):
    pattern = re.compile(
        r"^COPY public\.(\w+) \(([^)]+)\) FROM stdin;\n(.*?)^\\.$",
        re.MULTILINE | re.DOTALL,
    )

    with connection.cursor() as cursor:
        for table, columns, data in pattern.findall(dump_text):
            buffer = StringIO(data)
            cursor.copy_expert(
                f"COPY public.{table} ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')",
                buffer,
            )
    connection.commit()


def main():
    dump_text = read_dump(DUMP_PATH)
    connection = psycopg2.connect(DATABASE_URL, sslmode="require")
    connection.autocommit = False

    try:
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")

        statements = split_sql_statements(dump_text)
        with connection.cursor() as cursor:
            for statement in statements:
                upper = statement.upper()
                if upper.startswith("SET ") or upper.startswith("SELECT PG_CATALOG.SET_CONFIG"):
                    continue
                cursor.execute(statement)

        import_copy_blocks(connection, dump_text)
        connection.commit()
        print("Import completed successfully")
    except Exception as error:
        connection.rollback()
        print(f"Import failed: {error}")
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
