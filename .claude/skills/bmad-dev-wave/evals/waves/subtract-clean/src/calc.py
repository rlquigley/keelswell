def add(a, b):
    return a + b


def subtract(a, b):
    if b > a:
        raise ValueError("subtract would go below zero")
    return a - b
