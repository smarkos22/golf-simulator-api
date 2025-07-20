from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ Allow both local and deployed frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://golf-simulator-ui.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Golfer stats: (avg score, std dev, index)
GOLFER_DATA = {
    "Sean Farren": (70.9, 0.55, +1.6),
    "Andrej Erkelens": (78.1, 0.68, 2.2),
    "Nick Cutro": (80.2, 0.75, 3.2),
    "Nicholas Heflin": (80.5, 0.76, 6.0),
    "Cam Clark": (81.6, 0.78, 4.1),
    "Andrew Salzillo": (84.4, 0.83, 8.4),
    "Stephen Markos": (90.9, 0.92, 12.3),
    "Robert Wiseman": (93.0, 0.98, 14.8)
}

# ✅ Course data
COURSES = {
    "Boyne Highlands - Heather": {"Par": 72, "Rating": 75.4, "Slope": 147},
    "Boyne Highlands - Hills (Arthur Hills)": {"Par": 73, "Rating": 75.5, "Slope": 147},
    "Belvedere Golf Club": {"Par": 72, "Rating": 73.6, "Slope": 131},
    "Forest Dunes (Championship Course)": {"Par": 72, "Rating": 75.6, "Slope": 150},
    "The Loop (Forest Dunes, tips average)": {"Par": 70, "Rating": 71.9, "Slope": 125.5}
}

# ✅ Input format
class MatchInput(BaseModel):
    golfer1_name: str
    golfer2_name: str
    course_name: str
    manual_override: bool = False
    strokes_given: int = 0
    stroke_recipient: str = "golfer2"
    include_ties: bool = False

@app.post("/simulate")
def simulate_match(data: MatchInput):
    g1_mean, g1_std, g1_index = GOLFER_DATA[data.golfer1_name]
    g2_mean, g2_std, g2_index = GOLFER_DATA[data.golfer2_name]

    course = COURSES[data.course_name]
    slope_factor = course["Slope"] / 113
    g1_std *= slope_factor
    g2_std *= slope_factor

    g1_course_hcp = round(g1_index * slope_factor)
    g2_course_hcp = round(g2_index * slope_factor)

    default_strokes = abs(g1_course_hcp - g2_course_hcp)
    default_recipient = "golfer1" if g1_course_hcp > g2_course_hcp else "golfer2"

    strokes = data.strokes_given if data.manual_override else default_strokes
    recipient = data.stroke_recipient if data.manual_override else default_recipient

    n_simulations = 100_000
    n_holes = 18

    p1_scores = np.random.normal(g1_mean / n_holes, g1_std, (n_simulations, n_holes))
    p2_scores = np.random.normal(g2_mean / n_holes, g2_std, (n_simulations, n_holes))

    stroke_holes = np.zeros((n_simulations, n_holes))
    for i in range(n_simulations):
        stroke_indices = np.random.choice(n_holes, size=strokes, replace=False)
        stroke_holes[i, stroke_indices] = 1

    if recipient == "golfer1":
        p1_scores -= stroke_holes
    else:
        p2_scores -= stroke_holes

    p1_holes_won = (p1_scores < p2_scores).sum(axis=1)
    p2_holes_won = (p2_scores < p1_scores).sum(axis=1)

    p1_match_wins = p1_holes_won > p2_holes_won
    p2_match_wins = p2_holes_won > p1_holes_won
    ties = ~(p1_match_wins | p2_match_wins)

    def to_american_odds(prob):
        if prob == 0:
            return "∞"
        if prob >= 0.5:
            return f"{int(round(-100 * (prob / (1 - prob))))}"
        else:
            return f"+{int(round(100 * ((1 - prob) / prob)))}"

    p1_win_pct = np.mean(p1_match_wins)
    p2_win_pct = np.mean(p2_match_wins)
    tie_pct = np.mean(ties)

    if data.include_ties:
        return {
            "include_ties": True,
            "golfer1_win_pct": round(p1_win_pct * 100, 2),
            "golfer2_win_pct": round(p2_win_pct * 100, 2),
            "tied_match_pct": round(tie_pct * 100, 2),
            "course_slope_used": course["Slope"],
            "course_rating": course["Rating"],
            "course_par": course["Par"],
            "golfer1_index": g1_index,
            "golfer2_index": g2_index,
            "golfer1_course_handicap": g1_course_hcp,
            "golfer2_course_handicap": g2_course_hcp,
            "strokes_given": strokes,
            "stroke_recipient": recipient,
            "golfer1_odds": to_american_odds(p1_win_pct),
            "golfer2_odds": to_american_odds(p2_win_pct),
            "tie_odds": to_american_odds(tie_pct)
        }
    else:
        total = p1_win_pct + p2_win_pct
        p1_norm = p1_win_pct / total
        p2_norm = p2_win_pct / total
        return {
            "include_ties": False,
            "golfer1_win_pct": round(p1_norm * 100, 2),
            "golfer2_win_pct": round(p2_norm * 100, 2),
            "tied_match_pct": 0.0,
            "course_slope_used": course["Slope"],
            "course_rating": course["Rating"],
            "course_par": course["Par"],
            "golfer1_index": g1_index,
            "golfer2_index": g2_index,
            "golfer1_course_handicap": g1_course_hcp,
            "golfer2_course_handicap": g2_course_hcp,
            "strokes_given": strokes,
            "stroke_recipient": recipient,
            "golfer1_odds": to_american_odds(p1_norm),
            "golfer2_odds": to_american_odds(p2_norm),
            "tie_odds": None
        }
