def split(rows, cutoff):
    """Split (date, value) rows into (train, holdout) at cutoff, keeping order."""
    train = [row for row in rows if row[0] < cutoff]
    holdout = [row for row in rows if row[0] >= cutoff]
    if not train or not holdout:
        raise ValueError("cutoff leaves an empty window")
    return train, holdout
