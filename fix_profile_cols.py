# fix_profile_cols.py
from app import create_app, db
from sqlalchemy import text

def ensure_col(conn, table, name, type_="TEXT"):
    cols = [r[1] for r in conn.execute(text(f"PRAGMA table_info({table})")).all()]
    if name not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {type_}"))
        return True
    return False

def main():
    app = create_app()
    with app.app_context():
        engine = db.engine
        print("DB URL =", engine.url)

        with engine.begin() as conn:
            # Asegura columnas JSON guardadas como TEXT
            added = []
            if ensure_col(conn, "profile", "daily_goals", "TEXT"):
                conn.execute(text("UPDATE profile SET daily_goals='{}' WHERE daily_goals IS NULL"))
                added.append("daily_goals")

            if ensure_col(conn, "profile", "meal_plan", "TEXT"):
                conn.execute(text("UPDATE profile SET meal_plan='{}' WHERE meal_plan IS NULL"))
                added.append("meal_plan")

            if ensure_col(conn, "profile", "training_mods", "TEXT"):
                conn.execute(text("UPDATE profile SET training_mods='{}' WHERE training_mods IS NULL"))
                added.append("training_mods")

            cols_after = [r[1] for r in conn.execute(text("PRAGMA table_info(profile)")).all()]
            print("Añadidas:", added if added else "ninguna (ya existían)")
            print("Columnas profile:", cols_after)

if __name__ == "__main__":
    main()
