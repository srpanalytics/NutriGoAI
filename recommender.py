import pandas as pd
from utils import safe_div

# Mapping from friendly names to dataset columns
COL_MAP = {
    "calories": "Energy; enerc",
    "protein": "Protein; protcnt",
    "fiber": "Dietary Fiber; fibtg",
    "sugar": "Free Sugars; fsugar",
    "sat_fat": "Saturated Fatty acids; fasat",
    "sodium": "Sodium (Na); na",
    "cholesterol": "Cholesterol; cholc",
    "calcium": "Calcium (Ca); ca",
    "iron": "Iron (Fe); fe",
    "vitamin_c": "Ascorbic acids (C); vitc",
    "vitamin_a": "Vitamin A; vita",
    "polyphenols": "Polyphenols; polyph"
}

class Recommender:
    def __init__(self, data_path):
        self.df = pd.read_csv(data_path)
        self.df.columns = [c.strip() for c in self.df.columns]

        # Ensure all mapped columns exist
        for col in COL_MAP.values():
            if col not in self.df.columns:
                self.df[col] = 0.0

        # Convert to numeric
        for col in COL_MAP.values():
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)

    def _minmax(self, series):
        mn, mx = series.min(), series.max()
        if pd.isna(mn) or pd.isna(mx) or mx - mn == 0:
            return pd.Series(0.5, index=series.index)
        return (series - mn) / (mx - mn)

    def score_foods(self, targets, goal, nutrient_focus=None):
        df = self.df.copy()

        # Derived per-kcal metrics
        df['protein_per_kcal'] = df.apply(lambda r: safe_div(r[COL_MAP['protein']], r[COL_MAP['calories']] or 1), axis=1)
        df['fiber_per_kcal'] = df.apply(lambda r: safe_div(r[COL_MAP['fiber']], r[COL_MAP['calories']] or 1), axis=1)
        df['sugar_per_kcal'] = df.apply(lambda r: safe_div(r[COL_MAP['sugar']], r[COL_MAP['calories']] or 1), axis=1)
        df['satfat_per_kcal'] = df.apply(lambda r: safe_div(r[COL_MAP['sat_fat']], r[COL_MAP['calories']] or 1), axis=1)

        # Normalized metrics
        p = self._minmax(df['protein_per_kcal'])
        f = self._minmax(df['fiber_per_kcal'])
        s = 1.0 - self._minmax(df['sugar_per_kcal'])
        sat = 1.0 - self._minmax(df['satfat_per_kcal'])
        cal_norm = self._minmax(df[COL_MAP['calories']])
        low_cal = 1.0 - cal_norm
        high_cal = cal_norm
        vit_c = self._minmax(df[COL_MAP['vitamin_c']])
        iron = self._minmax(df[COL_MAP['iron']])
        calcium = self._minmax(df[COL_MAP['calcium']])
        polyphenols = self._minmax(df[COL_MAP['polyphenols']])

        # Goal-based weights
        if goal == "muscle":
            weights = dict(protein=3.0, fiber=0.8, low_sugar=0.6, low_satfat=0.8,
                           low_cal=0.0, high_cal=0.5, vit_c=0.3, iron=0.5)
        elif goal == "loss":
            weights = dict(protein=2.0, fiber=2.0, low_sugar=1.2, low_satfat=1.0,
                           low_cal=1.5, high_cal=0.0, vit_c=0.4, polyphenols=0.3)
        elif goal == "gain":
            weights = dict(protein=1.5, fiber=0.8, low_sugar=0.5, low_satfat=0.6,
                           low_cal=0.0, high_cal=1.5, iron=0.4)
        else:
            weights = dict(protein=1.5, fiber=1.0, low_sugar=0.8, low_satfat=0.8,
                           low_cal=0.6, high_cal=0.6)

        # Add nutrient focus boost
        if nutrient_focus == "High Protein":
            extra = p
        elif nutrient_focus == "High Fiber":
            extra = f
        elif nutrient_focus == "Low Sugar":
            extra = s
        elif nutrient_focus == "High Calcium":
            extra = calcium
        elif nutrient_focus == "High Iron":
            extra = iron
        elif nutrient_focus == "High Vitamin C":
            extra = vit_c
        else:
            extra = 0

        # Final score (kept internally)
        df['score'] = (
            weights['protein'] * p +
            weights['fiber'] * f +
            weights['low_sugar'] * s +
            weights['low_satfat'] * sat +
            weights.get('vit_c', 0) * vit_c +
            weights.get('iron', 0) * iron +
            weights.get('polyphenols', 0) * polyphenols +
            weights['low_cal'] * low_cal +
            weights['high_cal'] * high_cal +
            1.0 * extra
        )

        return df.sort_values(by='score', ascending=False)

    def recommend(self, targets, goal="maintenance", top_k=10, food_pref=None, nutrient_focus=None):
        df = self.score_foods(targets, goal, nutrient_focus)

        # Apply Veg/Non-Veg filter if provided
        if food_pref:
            if food_pref.lower() == "veg":
                df = df[~df['Food Group'].str.contains('meat|fish|egg', case=False, na=False)]
            elif food_pref.lower() == "non-veg":
                df = df[df['Food Group'].str.contains('meat|fish|egg', case=False, na=False)]

        # Only return user-facing columns
        cols_to_return = [
            "Food Name",
            COL_MAP['calories'],
            COL_MAP['protein'],
            COL_MAP['fiber'],
            COL_MAP['sugar']
        ]
        result_df = df[cols_to_return].head(top_k).copy()

        result_df.rename(columns={
            "Food Name": "Food",
            COL_MAP['calories']: "Calories",
            COL_MAP['protein']: "Protein",
            COL_MAP['fiber']: "Fiber",
            COL_MAP['sugar']: "Sugar"
        }, inplace=True)

        # Round values
        for c in ["Calories", "Protein", "Fiber", "Sugar"]:
            result_df[c] = result_df[c].apply(lambda x: round(float(x), 2))

        return result_df.to_dict(orient="records")
