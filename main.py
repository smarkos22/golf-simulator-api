from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np

app = FastAPI()

class MatchInput(BaseModel):
    golfer1_mean: float
    golfer1_std: float
    golfer2_mean: float
    golfer2_std: float
    strokes_given: int
    stroke_recipient: str

@app.post("/simulate")
def simulate_match(data: MatchInput):
    n_simulations = 100_000
    p1_scores = np.random.normal(data.golfer1_mean, data.golfer1_std, (n_simulations, 18))
    p2_scores = np.random.normal(data.golfer2_mean, data.golfer2_std, (n_simulations, 18))

    stroke_holes = np.zeros((n_simulations, 18))
    stroke_holes[:, :data.strokes_given] = 1

    if data.stroke_recipient == "golfer1":
        p1_scores -= stroke_holes
    else:
        p2_scores -= stroke_holes

    p1_wins = (p1_scores < p2_scores).sum(axis=1) > (p2_scores < p1_scores).sum(axis=1)
    p2_wins = ~p1_wins

    p1_win_pct = round(np.mean(p1_wins) * 100, 2)
    p2_win_pct = round(np.mean(p2_wins) * 100, 2)

    return {
        "golfer1_win_pct": p1_win_pct,
        "golfer2_win_pct": p2_win_pct
    }
