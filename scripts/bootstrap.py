# scripts/bootstrap.py
from sqlalchemy import text

from app import create_app, db

# Asegúrate de importar todos los modelos registrados
from app.models.user import User, Profile, Meal
from app.models.diary import DiaryDay, DiaryItem
from app.models.base_meals import BaseMeal, BaseMealSlot, SlotAlternative
from app.models.training import TrainingActual

from app.services.energy import compute_daily_goals_for_profile


SAFE_PROFILE_COLUMNS = {
    "daily_goals": "TEXT",
    "meal_plan": "TEXT",
    "training_mods": "TEXT",
}

SAFE_MEALS_COLUMNS = {
    # columnas que tu ORM declara y que pueden faltar en BD antigua
    "unit": "TEXT",
    "meal_type": "TEXT",
}


def ensure_profile_columns(conn):
    cols = [row[1] for row in conn.execute(text("PRAGMA table_info(profile)")).fetchall()]
    for col, sqltype in SAFE_PROFILE_COLUMNS.items():
        if col not in cols:
            conn.execute(text(f"ALTER TABLE profile ADD COLUMN {col} {sqltype}"))
            print(f"[schema] = profile.{col} AÑADIDA")
        else:
            print(f"[schema] = profile.{col} OK")


def ensure_meals_columns(conn):
    # Si la tabla no existe, create_all la creará antes
    cols = [row[1] for row in conn.execute(text("PRAGMA table_info(meals)")).fetchall()]
    for col, sqltype in SAFE_MEALS_COLUMNS.items():
        if col not in cols:
            conn.execute(text(f"ALTER TABLE meals ADD COLUMN {col} {sqltype}"))
            print(f"[schema] = meals.{col} AÑADIDA")
        else:
            print(f"[schema] = meals.{col} OK")


def ensure_daily_goals():
    empties = Profile.query.filter(
        (Profile.daily_goals.is_(None)) | (Profile.daily_goals == "")
    ).all()
    for p in empties:
        compute_daily_goals_for_profile(p)
        db.session.add(p)
    db.session.commit()
    print(f"[goals] perfiles actualizados: {len(empties)}")


def table_exists(conn, name: str) -> bool:
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).fetchone()
    return bool(row)


def main():
    app = create_app()
    with app.app_context():
        print("DB =>", app.config.get("SQLALCHEMY_DATABASE_URI"))

        # crea tablas faltantes
        db.create_all()

        # asegura columnas y muestra estado
        with db.engine.begin() as conn:
            ensure_profile_columns(conn)
            ensure_meals_columns(conn)

            for t in [
                "user",
                "profile",
                "meals",
                "diary_days",
                "diary_items",
                "base_meals",
                "base_meal_slots",
                "slot_alternatives",
                "training_actuals",
            ]:
                print(f"[table] {t:18s}", "OK" if table_exists(conn, t) else "FALTA")

        # rellena daily_goals donde esté vacío
        ensure_daily_goals()


if __name__ == "__main__":
    main()
