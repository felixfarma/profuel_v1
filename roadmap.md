# ROADMAP Profuel_v7_1

Este archivo define el camino priorizado para continuar el desarrollo del proyecto **Profuel_v7_1**, basado en el análisis de alto nivel y la decisión de arrancar por el registro de comidas.

---

## 1. Enfoque principal (fase actual)

**Fase 2: Registro de comidas**

1. **Paso 8 – Estructura de datos**
   - Revisar/actualizar modelo `Meal`:
     - `id`, `user_id` (FK → User), `food_id` (FK → Food)
     - `date` (Date), `time` (Time), `quantity` (Float)
     - (Opcional) campos cache (`calories`, `proteins`, `carbs`, `fats`)
     - Restricciones: `quantity > 0`, macros ≥ 0
   - Crear migración Alembic.

2. **Paso 9 – Formulario de registro de comidas**
   - `app/forms/meal_form.py` con WTForms:
     - `DateField`, `TimeField`, `SelectField(food choices)`, `FloatField(quantity)`
     - Validaciones (`NumberRange(min=0.01)`, CSRF)
   - Plantilla `templates/add_meal.html` (Tailwind/Bootstrap).

3. **Paso 10 – Rutas y controlador**
   - `GET /meals/new` → mostrar formulario
   - `POST /meals/new` → procesar, calcular valores, guardar `Meal`, redirigir

4. **Paso 11 – Listado diario**
   - Mostrar en el dashboard las comidas de hoy:
     - Hora, alimento, cantidad, kcal y macros

5. **Paso 12 – Gráficos de progreso**
   - Cálculo de totales diarios
   - Chart.js:
     - Gráfico de barras por comida
     - Barra de progreso vs objetivos diarios

---

## 2. Siguiente hito (fase futura)

**Calculadora Energética Avanzada**

6. **Refactor en `utils/calculos.py`**
   - Servicio/clase `EnergyCalculator`:
     - Métodos: `bmr()`, `tdee()`, `macros()`
   - Tests unitarios exhaustivos.

7. **Endpoint `/api/v1/calculator`**
   - Recibe perfil, devuelve BMR/TDEE/macros
   - Documentación OpenAPI.

---

## 3. Recomendaciones generales

- Versiona la API (`/api/v1/…`).
- Añade linting, typing, coverage CI.
- Implementa paginación y validación en endpoints.
- Mantén constraints en la base de datos.

---

*Este archivo debe ubicarse en la raíz del repositorio para informar rápidamente al equipo del plan de trabajo actual.*

