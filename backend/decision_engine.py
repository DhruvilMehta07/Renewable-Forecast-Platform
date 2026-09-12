"""
Rule-based decision engine, as scoped in the ideation report and Project_Plan.md.

Deliberately only fires during daytime: at night, near-zero generation is
expected and correct, not an anomaly needing a "backup_dispatch" flag on every
single night hour. The flags are meant to catch unexpected daytime deviations
(cloud cover suppressing output, or generation running high enough to need
curtailment) - not to restate that the sun is down.
"""

import config


def decide(predicted_kw: float, is_daytime: int, capacity_kw: float = None) -> str:
    capacity = capacity_kw or config.SITE_CAPACITY_KW
    frac = predicted_kw / capacity
    if is_daytime and frac >= config.CURTAIL_THRESHOLD_PCT:
        return "curtail"
    if is_daytime and frac <= config.UNDERPERFORM_THRESHOLD_PCT:
        return "backup_dispatch"
    return "normal"
