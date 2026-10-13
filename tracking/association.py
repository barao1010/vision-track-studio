"""GPL-2.0-or-later. Conservative selected-person box association."""

def overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    area = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(0, min(ay + ah, by + bh) - max(ay, by))
    return area / max(1, aw * ah + bw * bh - area)


def distinct_match(box, people):
    candidates = sorted([(overlap(box, person), person) for person in people], reverse=True)
    if not candidates or candidates[0][0] < .25:
        return None
    if len(candidates) > 1:
        if candidates[0][0] - candidates[1][0] < .15 or overlap(candidates[0][1], candidates[1][1]) > .12:
            return None
    return candidates[0][1]
