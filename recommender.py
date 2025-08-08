import pandas as pd
from utils import safe_div


class Recommender:
    def __init__(self, data_path):
        # Load CSV and clean columns
        self.df = pd.read_csv(data_path)
        self.df.columns = [c.strip() for c in self.df.columns]

        if "Food" not in self.df.columns:
            if len(self.df.columns) >= 1:
                self.df.rename(columns={self.df.columns[0]: "Food"}, inplace=True)
            else:
                raise ValueError("Dataset must contain at least one column with food names.")

        numeric_cols = [c for c in self.df.columns if c != "Food"]
        self.df[numeric_cols] = self.df[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    def _minmax(self, series):
        mn = series.min()
        mx = series.max()
        if pd.isna(mn) or pd.isna(mx) or mx - mn == 0:
            return pd.Series(0.5, index=series.index)
        return (series - mn) / (mx - mn)

    def score_foods(self, targets: dict, goal: str):
        df = self.df.copy()

        for col in ["Caloric Value", "Protein", "Dietary Fiber", "Sugars", "Sodium", "Saturated Fats", "Nutrition Density", "Cholesterol"]:
            if col not in df.columns:
                df[col] = 0.0

        df['protein_per_kcal'] = df.apply(lambda r: safe_div(r.get('Protein', 0), r.get('Caloric Value', 0) or 1), axis=1)
        df['fiber_per_kcal'] = df.apply(lambda r: safe_div(r.get('Dietary Fiber', 0), r.get('Caloric Value', 0) or 1), axis=1)
        df['sugar_per_kcal'] = df.apply(lambda r: safe_div(r.get('Sugars', 0), r.get('Caloric Value', 0) or 1), axis=1)
        df['sodium_per_kcal'] = df.apply(lambda r: safe_div(r.get('Sodium', 0), r.get('Caloric Value', 0) or 1), axis=1)
        df['satfat_per_kcal'] = df.apply(lambda r: safe_div(r.get('Saturated Fats', 0), r.get('Caloric Value', 0) or 1), axis=1)
        df['nutrition_density'] = df.get('Nutrition Density', pd.Series(0.0, index=df.index)).astype(float)

        p = self._minmax(df['protein_per_kcal'])
        f = self._minmax(df['fiber_per_kcal'])
        s = 1.0 - self._minmax(df['sugar_per_kcal'])     # low sugar better
        so = 1.0 - self._minmax(df['sodium_per_kcal'])   # low sodium better
        sat = 1.0 - self._minmax(df['satfat_per_kcal'])  # low saturated fat better
        d = self._minmax(df['nutrition_density'])

        cal_norm = self._minmax(df['Caloric Value'])
        low_cal = 1.0 - cal_norm     # higher for lower calorie foods
        high_cal = cal_norm          # higher for higher calorie foods

        g = (goal or "maintenance").lower()
        if g == "muscle":
            weights = dict(protein=3.0, fiber=0.8, low_sugar=0.6, low_sodium=0.6, low_satfat=0.6, density=1.0, low_cal=0.0, high_cal=0.2)
        elif g == "loss":
            weights = dict(protein=1.8, fiber=2.0, low_sugar=1.0, low_sodium=0.8, low_satfat=0.8, density=1.0, low_cal=1.5, high_cal=0.0)
        elif g == "gain":
            weights = dict(protein=1.2, fiber=0.6, low_sugar=0.3, low_sodium=0.5, low_satfat=0.4, density=0.8, low_cal=0.0, high_cal=1.5)
        else:  # maintenance / default
            weights = dict(protein=1.5, fiber=1.0, low_sugar=0.8, low_sodium=0.6, low_satfat=0.8, density=1.0, low_cal=0.6, high_cal=0.6)

        df['score'] = (
            weights['protein'] * p +
            weights['fiber'] * f +
            weights['low_sugar'] * s +
            weights['low_sodium'] * so +
            weights['low_satfat'] * sat +
            weights['density'] * d +
            weights['low_cal'] * low_cal +
            weights['high_cal'] * high_cal
        )

        if 'Cholesterol' in df.columns:
            chol_norm = self._minmax(df['Cholesterol'])
            df['score'] -= 0.2 * chol_norm

        return df.sort_values(by='score', ascending=False)

    def recommend(self, targets: dict, goal: str = "maintenance", top_k: int = 10):
        scored = self.score_foods(targets, goal)
        cols_to_return = [c for c in ["Food", "Caloric Value", "Protein", "Dietary Fiber", "Sugars", "Sodium", "score"] if c in scored.columns]
        result_df = scored[cols_to_return].head(top_k).copy()

        for c in result_df.columns:
            if c != "Food":
                result_df[c] = result_df[c].apply(lambda x: float(round(x, 3)))
        return result_df.to_dict(orient="records")
