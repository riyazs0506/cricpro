from datetime import date
from models import (
    db, Batch, PlayerStats, ManualScore, Player, MatchAssignment
)

# ----------------------------------------------------
# AGE CALCULATOR
# ----------------------------------------------------
def calculate_age(dob):
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

# ----------------------------------------------------
# ASSIGN BATCH BASED ON AGE RANGE
# ----------------------------------------------------
def assign_batch_by_age(age):
    if age is None:
        return None
    return Batch.query.filter(
        Batch.min_age <= age,
        Batch.max_age >= age
    ).first()


# ----------------------------------------------------
# GET ALLOWED PLAYERS (PLAYING XI or fallback approved)
# ----------------------------------------------------
def get_all_allowed_players(match_id):
    playing_ids = [
        p.player_id for p in MatchAssignment.query.filter_by(match_id=match_id).all()
    ]

    if playing_ids:
        return Player.query.filter(Player.id.in_(playing_ids)).all()

    # fallback — all approved players
    return Player.query.join(Player.user).filter_by(status="approved").all()


# ----------------------------------------------------
# MERGE MANUAL SCORE INTO PLAYER STATS
# Called ONLY when coach clicks APPROVE
# ----------------------------------------------------
def merge_manual_into_player_stats(match_id):
    rows = ManualScore.query.filter_by(match_id=match_id, is_opponent=False).all()
    if not rows:
        return

    per_player = {}

    for r in rows:
        if not r.player_id:
            continue

        pid = r.player_id

        if pid not in per_player:
            per_player[pid] = {
                "runs": 0, "balls": 0, "fours": 0, "sixes": 0,
                "outs": 0,
                "overs": 0.0, "runs_conceded": 0, "wickets": 0,
                "catches": 0, "drops": 0, "saves": 0
            }

        rec = per_player[pid]

        # ---------- BATTING ----------
        rec["runs"] += (r.runs or 0)
        rec["balls"] += (r.balls_faced or 0)
        rec["fours"] += (r.fours or 0)
        rec["sixes"] += (r.sixes or 0)

        if r.is_out:
            rec["outs"] += 1

        # ---------- BOWLING ----------
        rec["overs"] += float(r.overs or 0)
        rec["runs_conceded"] += (r.runs_conceded or 0)
        rec["wickets"] += (r.wickets or 0)

        # ---------- FIELDING ----------
        rec["catches"] += (r.catches or 0)
        rec["drops"] += (r.drops or 0)
        rec["saves"] += (r.saves or 0)

    # ---------- SAVE TO DB ----------
    for pid, vals in per_player.items():
        stats = PlayerStats.query.filter_by(player_id=pid).first()

        if not stats:
            stats = PlayerStats(player_id=pid)
            db.session.add(stats)
            db.session.flush()

        # Matches count increments ONCE per match
        stats.matches = (stats.matches or 0) + 1

        # Batting
        stats.total_runs += vals["runs"]
        stats.total_balls += vals["balls"]
        stats.total_fours += vals["fours"]
        stats.total_sixes += vals["sixes"]
        stats.outs += vals["outs"]

        # Bowling
        stats.overs_bowled += vals["overs"]
        stats.runs_conceded += vals["runs_conceded"]
        stats.wickets += vals["wickets"]

        # Fielding
        stats.catches += vals["catches"]
        stats.drops += vals["drops"]
        stats.saves += vals["saves"]

    db.session.commit()
