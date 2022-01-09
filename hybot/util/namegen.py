import namemaker
import random

from ..res.names import NAMES

try:
    while 1:
        nameset_2 = namemaker.make_name_set(NAMES, order=2)
        nameset_3 = namemaker.make_name_set(NAMES, order=3)
        nameset_4 = namemaker.make_name_set(NAMES, order=4)

        name_a = nameset_3.make_name(n_candidates=7,   pref_candidate=0, max_attempts=1000, exclude_real_names=True, add_to_history=True, exclude_history=False).replace('-', '')
        name_b = nameset_2.make_name(n_candidates=100, pref_candidate=2, max_attempts=1000, exclude_real_names=True, add_to_history=True, exclude_history=False).replace('-', '')
        name_c = nameset_4.make_name(n_candidates=6,   pref_candidate=2, max_attempts=1000, exclude_real_names=True, add_to_history=True, exclude_history=False).replace('-', '')
        name_d = random.choice(NAMES).replace(" ", "-")

        name = f"{name_b}-{name_a}-{name_c}".strip().replace(" ", "")

        print(f"Generated Name: {name} {name_d}")

except KeyboardInterrupt:
    pass
