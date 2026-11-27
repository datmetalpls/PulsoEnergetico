"""Pure previous-sample integration, shared by ingestion and comparison."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Interval:
    flag: str
    energy_wh: float = 0
    on_seconds: float = 0


def integrate(last_t_s, previous_power_w, t_s, sample_interval_s, *, gap_pending=False):
    if last_t_s is None:
        return Interval('ok')
    dt = t_s - last_t_s
    if dt < 0:
        return Interval('out_of_order')
    if gap_pending or dt > 3 * sample_interval_s:
        return Interval('gap_after')
    return Interval('ok', previous_power_w * dt / 3600, dt if previous_power_w > 0 else 0)
