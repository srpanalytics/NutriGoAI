from flask import Flask, render_template, request
from recommender import Recommender
from utils import calc_bmr, activity_multiplier, nutrient_targets
import config

app = Flask(__name__)

# Load recommender
recommender = Recommender(config.DATA_PATH)


@app.route("/", methods=["GET", "POST"])
def index():
    error = None

    if request.method == "POST":
        # Read raw form values as strings
        weight_str = request.form.get("weight", "").strip()
        height_str = request.form.get("height", "").strip()
        gender = request.form.get("gender", "").strip()
        age_str = request.form.get("age", "").strip()
        activity = request.form.get("activity", "").strip()
        goal = request.form.get("goal", "").strip()

        # Validate required inputs
        if not weight_str or not height_str or not gender or not activity or not goal:
            error = "Please fill in all required fields."
            return render_template("index.html", error=error, request=request)

        # Convert weight and height to float and check positive
        try:
            weight = float(weight_str)
            height = float(height_str)
            if weight <= 0 or height <= 0:
                raise ValueError
        except ValueError:
            error = "Weight and height must be positive numbers."
            return render_template("index.html", error=error, request=request)

        # Age is optional; default to 30 if empty or invalid
        try:
            age = int(age_str) if age_str else 30
            if age <= 0 or age > 120:
                age = 30
        except ValueError:
            age = 30

        # Compute BMR, TDEE, targets
        bmr = calc_bmr(weight, height, age, gender)
        tdee = bmr * activity_multiplier(activity)
        targets = nutrient_targets(tdee, goal, weight)

        # Get recommendations
        try:
            recommendations = recommender.recommend(targets, goal, top_k=config.TOP_K)
        except Exception as e:
            error = f"Error generating recommendations: {e}"
            return render_template("index.html", error=error, request=request)

        return render_template(
            "results.html",
            results=recommendations,
            message=f"Top {config.TOP_K} foods for goal: {goal.capitalize()}",
            targets=targets
        )

    # GET request - show empty form, no results
    return render_template("index.html")
    

if __name__ == "__main__":
    app.run(debug=True)
