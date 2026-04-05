import time
from collections import defaultdict

POSTS_PER_HOUR = 5
COOLDOWN_SECONDS = 10 # 5 Minutes

_timestamps: dict[str, list[float]] = defaultdict(list)

def check_rate_limit(ip: str) -> tuple[bool, str]:
    now = time.time()
    times = _timestamps[ip]

    # Clear timestamps older than 1 hour
    times[:] = [t for t in times if now - t < 3600]

    if times and now - times[-1] < COOLDOWN_SECONDS:
        wait = int(COOLDOWN_SECONDS - (now - times[-1]))
        return False, f"Vänta {wait} sekunder innan nästa inlägg"
    
    if len(times) >= POSTS_PER_HOUR:
        return False, "Du har nått maxgränsen på 5 inlägg per timme."
    
    return True, ""

def record_post(ip: str) -> None:
    _timestamps[ip].append(time.time())
