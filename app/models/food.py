from app import db

class Food(db.Model):
    __tablename__ = 'foods'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)

    # Valores por 100 g
    kcal_per_100g    = db.Column(db.Float, nullable=True)
    protein_per_100g = db.Column(db.Float, nullable=True)
    carbs_per_100g   = db.Column(db.Float, nullable=True)
    fat_per_100g     = db.Column(db.Float, nullable=True)

    # Valores por unidad
    kcal_per_unit    = db.Column(db.Float, nullable=True)
    protein_per_unit = db.Column(db.Float, nullable=True)
    carbs_per_unit   = db.Column(db.Float, nullable=True)
    fat_per_unit     = db.Column(db.Float, nullable=True)

    # Unidad y cantidad de porción por defecto
    default_unit     = db.Column(db.String(20), nullable=False, default='g')
    default_quantity = db.Column(db.Float, nullable=False, default=100.0)

    def __repr__(self):
        return f'<Food {self.name}>'
