# scripts/seed_foods.py
from __future__ import annotations

"""
Siembra la tabla 'foods' con una lista curada de alimentos (macros por 100 g/ml).
- Compatible con dos esquemas:
  * Nuevo:  kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g
            + (opcional) *_per_unit
  * Antiguo: kcal, pro_g, cho_g, fat_g  + per_100g = 1
- Rellena default_unit y default_quantity.
- Garantiza que 'meals' tenga columna 'unit'.
"""

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app import create_app, db

# =========================
# 1) ALIMENTOS (por 100 g/ml)
# =========================
# Nota: valores aproximados y habituales en ES. Puedes ajustarlos cuando quieras.
FOODS = [
    # nombre, unidad base, kcal /100, carbs /100, pro /100, fat /100
    {"name": "leche semidesnatada consum", "unit": "ml", "kcal": 47,  "cho_g": 4.9,  "pro_g": 3.4, "fat_g": 1.6},
    {"name": "pan semillas consum",        "unit": "g",  "kcal": 280, "cho_g": 43,   "pro_g": 10,  "fat_g": 6},
    {"name": "philadelphia",               "unit": "g",  "kcal": 253, "cho_g": 4,    "pro_g": 6,   "fat_g": 24},
    {"name": "crema cacahuete crunchy",    "unit": "g",  "kcal": 600, "cho_g": 14,   "pro_g": 25,  "fat_g": 50},
    {"name": "tahini",                      "unit": "g",  "kcal": 595, "cho_g": 17,   "pro_g": 26,  "fat_g": 53},
    {"name": "yogur griego light aldi",    "unit": "g",  "kcal": 59,  "cho_g": 3.5,  "pro_g": 10,  "fat_g": 0.4},
    {"name": "aceite de oliva",            "unit": "ml", "kcal": 884, "cho_g": 0,    "pro_g": 0,   "fat_g": 100},
    {"name": "pechuga pavo asada",         "unit": "g",  "kcal": 110, "cho_g": 1,    "pro_g": 24,  "fat_g": 1.5},
    {"name": "queso havarti lonchas",      "unit": "g",  "kcal": 371, "cho_g": 2,    "pro_g": 21,  "fat_g": 31},
    {"name": "jamon serrano",              "unit": "g",  "kcal": 241, "cho_g": 0.5,  "pro_g": 31,  "fat_g": 13},
    {"name": "macarrones secos",           "unit": "g",  "kcal": 350, "cho_g": 72,   "pro_g": 12,  "fat_g": 1.5},
    {"name": "arroz blanco cocido",        "unit": "g",  "kcal": 130, "cho_g": 28,   "pro_g": 2.7, "fat_g": 0.3},
    {"name": "chia",                        "unit": "g",  "kcal": 486, "cho_g": 42,   "pro_g": 17,  "fat_g": 31},
    {"name": "platano",                     "unit": "g",  "kcal": 89,  "cho_g": 23,   "pro_g": 1.1, "fat_g": 0.3},
    {"name": "arandanos",                   "unit": "g",  "kcal": 57,  "cho_g": 14.5, "pro_g": 0.7, "fat_g": 0.3},
    {"name": "fresas",                      "unit": "g",  "kcal": 32,  "cho_g": 7.7,  "pro_g": 0.7, "fat_g": 0.3},
    {"name": "nutella",                     "unit": "g",  "kcal": 539, "cho_g": 57.5, "pro_g": 6.3, "fat_g": 30.9},
    {"name": "chocapic",                    "unit": "g",  "kcal": 393, "cho_g": 77,   "pro_g": 7.5, "fat_g": 4.5},
    {"name": "colacao",                     "unit": "g",  "kcal": 379, "cho_g": 85,   "pro_g": 5.7, "fat_g": 3.5},
    {"name": "tomate pera",                 "unit": "g",  "kcal": 18,  "cho_g": 3.9,  "pro_g": 0.9, "fat_g": 0.2},
    {"name": "cebolla tierna",              "unit": "g",  "kcal": 32,  "cho_g": 7.3,  "pro_g": 1.1, "fat_g": 0.1},
    {"name": "lomo de cerdo",               "unit": "g",  "kcal": 242, "cho_g": 0,    "pro_g": 27,  "fat_g": 14},
    {"name": "pechuga de pollo",            "unit": "g",  "kcal": 165, "cho_g": 0,    "pro_g": 31,  "fat_g": 3.6},
    {"name": "dorada",                      "unit": "g",  "kcal": 96,  "cho_g": 0,    "pro_g": 20,  "fat_g": 2.7},
    {"name": "salmon",                      "unit": "g",  "kcal": 208, "cho_g": 0,    "pro_g": 20,  "fat_g": 13},
    {"name": "atun lata natural",           "unit": "g",  "kcal": 116, "cho_g": 0,    "pro_g": 26,  "fat_g": 1},
]

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS foods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
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
    # 1) Crea tabla si no existe (mínima)
    conn.execute(text(CREATE_TABLE))

    # 2) Nuevo esquema (preferente)
    add_col(conn, "foods", "default_unit TEXT")
    add_col(conn, "foods", "default_quantity REAL")
    add_col(conn, "foods", "kcal_per_100g REAL")
    add_col(conn, "foods", "protein_per_100g REAL")
    add_col(conn, "foods", "carbs_per_100g REAL")
    add_col(conn, "foods", "fat_per_100g REAL")
    add_col(conn, "foods", "kcal_per_unit REAL")
    add_col(conn, "foods", "protein_per_unit REAL")
    add_col(conn, "foods", "carbs_per_unit REAL")
    add_col(conn, "foods", "fat_per_unit REAL")

    # 3) Viejo esquema (compatibilidad)
    add_col(conn, "foods", "unit TEXT")
    add_col(conn, "foods", "per_100g INTEGER")
    add_col(conn, "foods", "kcal REAL")
    add_col(conn, "foods", "cho_g REAL")
    add_col(conn, "foods", "pro_g REAL")
    add_col(conn, "foods", "fat_g REAL")

    # sanea nulos típicos
    conn.execute(text("UPDATE foods SET default_unit = COALESCE(default_unit, 'g')"))
    conn.execute(text("UPDATE foods SET default_quantity = COALESCE(default_quantity, 100)"))
    conn.execute(text("UPDATE foods SET unit = COALESCE(unit, default_unit, 'g')"))
    conn.execute(text("UPDATE foods SET per_100g = COALESCE(per_100g, 1)"))

    # índice por nombre
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

def build_upsert(conn) -> tuple[str, list[str]]:
    """
    Devuelve el SQL de upsert y el listado de columnas admitidas
    (según las realmente existentes en 'foods').
    """
    cols = get_cols(conn, "foods")

    # Intentamos poblar ambos esquemas si existen
    preferred = [
        "name", "default_unit", "default_quantity",
        "kcal_per_100g", "protein_per_100g", "carbs_per_100g", "fat_per_100g",
        "kcal_per_unit", "protein_per_unit", "carbs_per_unit", "fat_per_unit",
    ]
    legacy = [
        "unit", "per_100g", "kcal", "cho_g", "pro_g", "fat_g",
    ]

    ins = [c for c in preferred + legacy if c in cols]
    placeholders = [f":{c}" for c in ins]
    set_list = [f"{c}=excluded.{c}" for c in ins if c != "name"]

    sql = f"""
        INSERT INTO foods ({", ".join(ins)})
        VALUES ({", ".join(placeholders)})
        ON CONFLICT(name) DO UPDATE SET
            {", ".join(set_list)};
    """
    return sql, ins

def upsert_foods(conn) -> int:
    sql, ins_cols = build_upsert(conn)
    n = 0
    for f in FOODS:
        # Valores base por 100 g/ml
        kcal = float(f["kcal"])
        pro  = float(f["pro_g"])
        cho  = float(f["cho_g"])
        fat  = float(f["fat_g"])
        unit = f["unit"]

        params = {c: None for c in ins_cols}
        params["name"] = f["name"]

        # Nuevo esquema
        if "default_unit" in ins_cols:    params["default_unit"] = unit
        if "default_quantity" in ins_cols:params["default_quantity"] = 100
        if "kcal_per_100g" in ins_cols:   params["kcal_per_100g"] = kcal
        if "protein_per_100g" in ins_cols:params["protein_per_100g"] = pro
        if "carbs_per_100g" in ins_cols:  params["carbs_per_100g"] = cho
        if "fat_per_100g" in ins_cols:    params["fat_per_100g"] = fat
        # Por unidad (no definidos por ahora; se quedan NULL)
        if "kcal_per_unit" in ins_cols:   params["kcal_per_unit"] = None
        if "protein_per_unit" in ins_cols:params["protein_per_unit"] = None
        if "carbs_per_unit" in ins_cols:  params["carbs_per_unit"] = None
        if "fat_per_unit" in ins_cols:    params["fat_per_unit"] = None

        # Esquema antiguo (compat)
        if "unit" in ins_cols:            params["unit"] = unit
        if "per_100g" in ins_cols:        params["per_100g"] = 1
        if "kcal" in ins_cols:            params["kcal"] = kcal
        if "pro_g" in ins_cols:           params["pro_g"] = pro
        if "cho_g" in ins_cols:           params["cho_g"] = cho
        if "fat_g" in ins_cols:           params["fat_g"] = fat

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
