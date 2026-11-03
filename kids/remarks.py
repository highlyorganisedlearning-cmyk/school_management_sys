REMARK_MAP = {
    # NEGATIVE TRENDS - 10 sets
    'N10': (-100, -51, [
        "Severe drop in performance. Urgent intervention required.",
        "Significant decline. Needs immediate remedial work.",
        "Drastic fall in standard. Requires close supervision."
    ]),
    'N9': (-50, -41, [
        "Sharp decline observed. Needs to redouble efforts.",
        "Marked drop. Must revisit fundamentals.",
        "Considerable decrease. Extra work needed."
    ]),
    'N8': (-40, -31, [
        "Worrying downward trend. Needs to work harder.",
        "Performance has slipped notably. Requires attention.",
        "Consistent effort lacking. Must improve."
    ]),
    'N7': (-30, -26, [
        "Performance below expected level. Needs to pull up.",
        "Drop in attainment. More revision required.",
        "Below previous standard. Needs guidance."
    ]),
    'N6': (-25, -21, [
        "Slight but clear decline. Needs to focus more.",
        "Performance has dipped. Must be more consistent.",
        "Needs to avoid complacency."
    ]),
    'N5': (-20, -16, [
        "Some decline noted. Requires more practice.",
        "Performance has fallen slightly. Can do better.",
        "Needs to improve concentration."
    ]),
    'N4': (-15, -11, [
        "Minor drop. Needs to maintain previous effort.",
        "Slight decline. Requires steady revision.",
        "Needs to be more attentive in class."
    ]),
    'N3': (-10, -6, [
        "Almost maintaining standard. Needs little more push.",
        "Marginal decline. Can recover easily.",
        "Needs to sustain effort."
    ]),
    'N2': (-5, -3, [
        "Slightly below previous. Needs consistency.",
        "Performance fairly stable. Slight improvement needed.",
        "Needs to keep up momentum."
    ]),
    'N1': (-2, -1, [
        "Performance steady with slight fluctuation.",
        "Maintaining average. Needs to aim higher.",
        "Fair performance. More effort required."
    ]),

    # NEUTRAL
    'Z0': (0, 0, [
        "Performance maintained at same level.",
        "Steady progress observed. Keep it up.",
        "Consistent performance."
    ]),

    # POSITIVE TRENDS - 10 sets
    'P1': (1, 2, [
        "Slight improvement noted. Keep it up.",
        "Marginal gain observed. More effort needed.",
        "Moving in right direction."
    ]),
    'P2': (3, 5, [
        "Fair improvement shown. Can do better.",
        "Encouraging progress. Maintain effort.",
        "Shows signs of improvement."
    ]),
    'P3': (6, 10, [
        "Good improvement. Maintain the momentum.",
        "Positive progress noted. Keep working hard.",
        "Improved performance. Well done."
    ]),
    'P4': (11, 15, [
        "Commendable improvement. Keep it up.",
        "Good progress. Shows commitment.",
        "Noticeable improvement. Well done."
    ]),
    'P5': (16, 20, [
        "Very good improvement. Keep up the hard work.",
        "Impressive progress. Continue like this.",
        "Strong improvement shown."
    ]),
    'P6': (21, 25, [
        "Excellent improvement. Highly commendable.",
        "Remarkable progress. Keep it up.",
        "Great improvement in performance."
    ]),
    'P7': (26, 30, [
        "Outstanding improvement. Keep the spirit.",
        "Excellent work. Shows great potential.",
        "Tremendous progress. Well done."
    ]),
    'P8': (31, 40, [
        "Exceptional improvement. Very impressive.",
        "Huge leap in performance. Highly commendable.",
        "Fantastic progress. Keep it up."
    ]),
    'P9': (41, 50, [
        "Extraordinary improvement. Top effort.",
        "Excellent turnaround. Keep soaring.",
        "Brilliant improvement. Well done."
    ]),
    'P10': (51, 100, [
        "Phenomenal improvement. Keep excelling.",
        "Outstanding turnaround. Excellent work.",
        "Superb progress. Highly impressive."
    ]),
}


def get_remark_data(trend):
    if trend is None:
        return None, []
    try:
        t = float(trend)
    except:
        return None, []
    if t > 100 or t < -100:
        return "ERROR", ["Error in Input Marks"]
    for group, (low, high, options) in REMARK_MAP.items():
        if low <= t <= high:
            return group, options
    return None, []
