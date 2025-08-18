# scripts/seed_foods.py
from __future__ import annotations
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app import create_app, db

FOODS = [
    # name, unit, kcal, cho_g, pro_g, fat_g  (valores por 100 g o 100 ml)
    {"name": "leche semidesnatada", "unit": "ml", "kcal": 46,  "cho_g": 4.8,  "pro_g": 3.4,  "fat_g": 1.5},
    {"name": "pan semillas consum", "unit": "g",  "kcal": 280, "cho_g": 43,   "pro_g": 10,   "fat_g": 6},
    {"name": "crema cacahuete con trozos wenatural", "unit": "g", "kcal": 600, "cho_g": 14, "pro_g": 25, "fat_g": 50},
    {"name": "pechuga pavo asada", "unit": "g",    "kcal": 110, "cho_g": 1,   "pro_g": 24,  "fat_g": 1.5},
    {"name": "queso havarti", "unit": "g",         "kcal": 371, "cho_g": 2,   "pro_g": 21,  "fat_g": 31},
    {"name": "queso cottage proteinas arla", "unit": "g", "kcal": 82, "cho_g": 3, "pro_g": 12, "fat_g": 2},
    {"name": "yogur griego light aldi", "unit": "g","kcal": 59,  "cho_g": 3.5, "pro_g": 10,  "fat_g": 0.4},
    {"name": "quinoa inflada", "unit": "g",        "kcal": 368, "cho_g": 64,  "pro_g": 13,  "fat_g": 6},
    {"name": "chia", "unit": "g",                  "kcal": 486, "cho_g": 42,  "pro_g": 17,  "fat_g": 31},
    {"name": "platano de canarias", "unit": "g",   "kcal": 89,  "cho_g": 23,  "pro_g": 1.1, "fat_g": 0.3},
    {"name": "patata asada", "unit": "g",          "kcal": 93,  "cho_g": 21,  "pro_g": 2.5, "fat_g": 0.1},
    {"name": "salmon fresco", "unit": "g",         "kcal": 208, "cho_g": 0,   "pro_g": 20,  "fat_g": 13},
    {"name": "pechuga de pollo", "unit": "g",      "kcal": 165, "cho_g": 0,   "pro_g": 31,  "fat_g": 3.6},
    {"name": "lata atun al natural consum", "unit": "g", "kcal": 116, "cho_g": 0, "pro_g": 26, "fat_g": 1},
    {"name": "chocapic", "unit": "g",              "kcal": 393, "cho_g": 77,  "pro_g": 7.5, "fat_g": 4.5},
    {"name": "huevo", "unit": "g",                 "kcal": 155, "cho_g": 1.1, "pro_g": 13,  "fat_g": 11},
    {"name": "pipas de girasol peladas", "unit": "g","kcal": 584,"cho_g": 20, "pro_g": 21,  "fat_g": 51},
    {"name": "dorada", "unit": "g",                "kcal": 96,  "cho_g": 0,   "pro_g": 20,  "fat_g": 2.7},
    {"name": "lubina", "unit": "g",                "kcal": 97,  "cho_g": 0,   "pro_g": 20,  "fat_g": 2},
    {"name": "nutella", "unit": "g",               "kcal": 539, "cho_g": 57.5,"pro_g": 6.3, "fat_g": 30.9},
    {"name": "tahini monki", "unit": "g",          "kcal": 595, "cho_g": 17,  "pro_g": 26,  "fat_g": 53},
    {"name": "galletas maria dorada consum", "unit": "g","kcal": 480,"cho_g": 74,"pro_g": 7, "fat_g": 19},
]

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS foods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    unit TEXT,
    default_unit TEXT,
    default_quantity REAL,
    per_100g INTEGER,
    kcal REAL,
    cho_g REAL,
    pro_g REAL,
    fat_g REAL
);
"""

def table_exists(conn, name: str) -> bool:
    r = conn.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:n"
    ), {"n": name}).fetchone()
    return r is not None

def get_cols(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}

def add_col(conn, table: str, decl: str):
    # decl: "colname TYPE [DEFAULT ...] [NOT NULL]"
    col = decl.split()[0]
    if col not in get_cols(conn, table):
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {decl}"))
        print(f"[{table}] + columna añadida: {decl}")

def ensure_foods_schema(conn):
    # crea tabla si no existe
    conn.execute(text(CREATE_TABLE))

    # añade columnas que falten, con DEFAULT para evitar NOT NULL failures
    add_col(conn, "foods", "unit TEXT")
    add_col(conn, "foods", "default_unit TEXT DEFAULT 'g'")
    add_col(conn, "foods", "default_quantity REAL DEFAULT 100")
    add_col(conn, "foods", "per_100g INTEGER DEFAULT 1")
    add_col(conn, "foods", "kcal REAL")
    add_col(conn, "foods", "cho_g REAL")
    add_col(conn, "foods", "pro_g REAL")
    add_col(conn, "foods", "fat_g REAL")

    # sanea nulos existentes
    conn.execute(text("UPDATE foods SET unit = COALESCE(unit, default_unit, 'g')"))
    conn.execute(text("UPDATE foods SET default_unit = COALESCE(default_unit, unit, 'g')"))
    conn.execute(text("UPDATE foods SET default_quantity = COALESCE(default_quantity, 100)"))
    conn.execute(text("UPDATE foods SET per_100g = COALESCE(per_100g, 1)"))

    # índices
    try:
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_foods_name ON foods(name)"))
    except OperationalError:
        pass

def ensure_meals_unit(conn):
    if not table_exists(conn, "meals"):
        return
    cols = get_cols(conn, "meals")
    if "unit" not in cols:
        add_col(conn, "meals", "unit TEXT")
        conn.execute(text("UPDATE meals SET unit = COALESCE(unit,'g')"))

def build_upsert(conn) -> str:
    cols = get_cols(conn, "foods")
    ins = ["name", "default_unit", "unit", "default_quantity", "per_100g", "kcal", "cho_g", "pro_g", "fat_g"]
    ins = [c for c in ins if c in cols]
    placeholders = [f":{c}" for c in ins]
    set_list = [f"{c}=excluded.{c}" for c in ins if c != "name"]
    return f"""
        INSERT INTO foods ({", ".join(ins)})
        VALUES ({", ".join(placeholders)})
        ON CONFLICT(name) DO UPDATE SET
            {", ".join(set_list)};
    """, ins

def upsert_foods(conn):
    sql, ins_cols = build_upsert(conn)
    n = 0
    for f in FOODS:
        params = {c: None for c in ins_cols}
        params["name"] = f["name"]
        # defaults coherentes
        if "unit" in ins_cols:
            params["unit"] = f["unit"]
        if "default_unit" in ins_cols:
            params["default_unit"] = f["unit"]
        if "default_quantity" in ins_cols:
            params["default_quantity"] = 100
        if "per_100g" in ins_cols:
            params["per_100g"] = 1
        params["kcal"] = f["kcal"]
        params["cho_g"] = f["cho_g"]
        params["pro_g"] = f["pro_g"]
        params["fat_g"] = f["fat_g"]
        conn.execute(text(sql), params)
        n += 1
    return n

def main():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()
        ensure_foods_schema(conn)
        ensure_meals_unit(conn)
        n = upsert_foods(conn)
        conn.commit()
        print(f"[foods] semilla aplicada/actualizada: {n} alimentos")

if __name__ == "__main__":
    main()
