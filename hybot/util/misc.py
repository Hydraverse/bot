
def ordinal(n: int) -> str:
    """Return the ordinated number, e.g. 1st.
    """
    return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])
