from flask import Flask, render_template, request
from recommender import Recommender
from utils import calc_bmr, activity_multiplier, nutrient_targets
import config
import os

app = Flask(__name__)

# Load recommender
recommender = Recommender(config.DATA_PATH)

# Dropdown options
veg_tags = ["Veg", "Non-Veg"]
nutrient_focus_list = [
    "None", "High Protein", "High Fiber", "Low Sugar",
    "High Calcium", "High Iron", "High Vitamin C"
]

@app.route("/", methods=["GET", "POST"])
def index():
    error = None

    if request.method == "POST":
        # Required inputs
        weight_str = request.form.get("weight", "").strip()
        height_str = request.form.get("height", "").strip()
        gender = request.form.get("gender", "").strip()
        age_str = request.form.get("age", "").strip()
        activity = request.form.get("activity", "").strip()
        goal = request.form.get("goal", "").strip()

        # Optional inputs
        food_pref = request.form.get("food_pref", "").strip()
        nutrient_focus = request.form.get("nutrient_focus", "None").strip()

        # Validation
        if not weight_str or not height_str or not gender or not activity or not goal:
            error = "Please fill in all required fields."
            return render_template(
                "index.html", error=error, request=request,
                veg_tags=veg_tags, nutrient_focus_list=nutrient_focus_list
            )

        try:
            weight = float(weight_str)
            height = float(height_str)
            if weight <= 0 or height <= 0:
                raise ValueError
        except ValueError:
            error = "Weight and height must be positive numbers."
            return render_template(
                "index.html", error=error, request=request,
                veg_tags=veg_tags, nutrient_focus_list=nutrient_focus_list
            )

        # Process age
        try:
            age = int(age_str) if age_str else 30
            if age <= 0 or age > 120:
                age = 30
        except ValueError:
            age = 30

        # Calculate targets
        bmr = calc_bmr(weight, height, age, gender)
        tdee = bmr * activity_multiplier(activity)
        targets = nutrient_targets(tdee, goal, weight)

        # Get recommendations
        try:
            recommendations = recommender.recommend(
                targets, goal, top_k=config.TOP_K,
                food_pref=food_pref if food_pref else None,
                nutrient_focus=nutrient_focus if nutrient_focus != "None" else None
            )
        except Exception as e:
            error = f"Error generating recommendations: {e}"
            return render_template(
                "index.html", error=error, request=request,
                veg_tags=veg_tags, nutrient_focus_list=nutrient_focus_list
            )

        return render_template(
            "results.html",
            results=recommendations,
            message=f"Top {config.TOP_K} foods for goal: {goal.capitalize()}",
            targets=targets
        )

    # GET — load empty form
    return render_template(
        "index.html",
        veg_tags=veg_tags,
        nutrient_focus_list=nutrient_focus_list
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)
