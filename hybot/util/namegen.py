import sys

import namemaker

from ..res.names import NAMES

nameset_a = namemaker.make_name_set(NAMES, order=3)
nameset_b = namemaker.make_name_set(NAMES, order=2)
nameset_c = namemaker.make_name_set(NAMES, order=4)


def make_name():
    while 1:
        name_a = nameset_a.make_name(n_candidates=5,   pref_candidate=2, max_attempts=50, exclude_real_names=True, add_to_history=False, exclude_history=False)
        name_b = nameset_b.make_name(n_candidates=6,   pref_candidate=0, max_attempts=100, exclude_real_names=True, add_to_history=False, exclude_history=False)
        name_c = nameset_c.make_name(n_candidates=300, pref_candidate=2, max_attempts=10, exclude_real_names=True, add_to_history=False, exclude_history=False)

        # if "hy" in name_a.lower() or "hy" in name_b.lower() or "hy" in name_c.lower():
        if name_b.lower().startswith("hy") or name_a.lower().startswith("hy") or name_c.lower().startswith("hy"):
            return name_a, name_b, name_c


if __name__ == "__main__":
    try:
        while 1:
            print(" ".join(make_name()))
    except KeyboardInterrupt:
        print(file=sys.stderr)
        pass
