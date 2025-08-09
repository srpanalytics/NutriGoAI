def calc_bmr(weight_kg, height_cm, age, gender):
    gender = (gender or "").lower()
    if gender in ("m", "male"):
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

def activity_multiplier(level):
    mapping = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    return mapping.get((level or "moderate").lower(), 1.55)

def nutrient_targets(tdee, goal, weight_kg):
    goal = (goal or "maintenance").lower()
    if goal == "loss":
        calories = max(tdee - 500, 1200)
    elif goal == "gain":
        calories = tdee + 300
    else:
        calories = tdee

    if goal == "muscle":
        protein_g = weight_kg * 1.8
    elif goal == "gain":
        protein_g = weight_kg * 1.6
    else:
        protein_g = weight_kg * 1.2

    fat_g = (0.25 * calories) / 9
    carbs_kcal = calories - (protein_g * 4 + fat_g * 9)
    carbs_g = max(carbs_kcal / 4, 0)

    return {
        "calories": round(calories),
        "protein_g": round(protein_g, 1),
        "fat_g": round(fat_g, 1),
        "carbs_g": round(carbs_g, 1),
    }

def safe_div(a, b):
    try:
        return a / b if b else 0.0
    except Exception:
        return 0.0
