import math
import time

from hub.lang import T


perf = time.perf_counter


def mean(v):
    return sum(v) / len(v) if v else 0.0


def stdev(v):
    if len(v) < 2:
        return 0.0
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / len(v))


def rms(v):
    return math.sqrt(sum(x * x for x in v) / len(v)) if v else 0.0


def freq_of(ts, vs):
    if len(vs) < 6:
        return None
    lo, hi = min(vs), max(vs)
    if hi - lo < 1e-3:
        return None
    m = (lo + hi) / 2
    h = (hi - lo) * 0.1
    state = vs[0] > m
    cross = []
    for i in range(1, len(vs)):
        if not state and vs[i] > m + h:
            state = True
            j = i
            while j > 0 and vs[j - 1] > m:
                j -= 1
            if j > 0 and vs[j] != vs[j - 1]:
                f = (m - vs[j - 1]) / (vs[j] - vs[j - 1])
                cross.append(ts[j - 1] + f * (ts[j] - ts[j - 1]))
            else:
                cross.append(ts[i])
        elif state and vs[i] < m - h:
            state = False
    if len(cross) < 2 or cross[-1] <= cross[0]:
        return None
    return (len(cross) - 1) / (cross[-1] - cross[0])


def sine_fit(ts, vs, f):
    w = 2 * math.pi * f
    A = [[0.0] * 3 for _ in range(3)]
    B = [0.0] * 3
    for t, v in zip(ts, vs):
        row_ = (math.sin(w * t), math.cos(w * t), 1.0)
        for i in range(3):
            B[i] += row_[i] * v
            for j in range(3):
                A[i][j] += row_[i] * row_[j]
    M = [A[i] + [B[i]] for i in range(3)]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12:
            return 0.0, 0.0, mean(vs)
        for r in range(3):
            if r != c:
                k = M[r][c] / M[c][c]
                for j in range(c, 4):
                    M[r][j] -= k * M[c][j]
    a, b, cc = (M[i][3] / M[i][i] for i in range(3))
    return math.hypot(a, b), math.atan2(b, a), cc


def nice_step(span, n=8):
    raw = span / float(n)
    e = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if raw <= m * e:
            return m * e
    return 10 * e


def nice_range(lo, hi, n=8, zero=False):
    if zero:
        lo = min(lo, 0.0)
        hi = max(hi, 0.0)
    if hi - lo < 1e-9:
        hi, lo = hi + 0.5, lo - 0.5
    st = nice_step(hi - lo, n)
    lo = math.floor(lo / st) * st
    hi = math.ceil(hi / st) * st
    return lo, hi, max(1, int(round((hi - lo) / st)))


def ai_items(dev):
    return [(i, t) for i, t in enumerate(dev.channels("ai"))]


COMMON_HELP = (T("\n\nEntradas: de 0 V a Vref (3.3 V en ESP32/K8, 5 V en UNO/Nano). Nunca "
                 "apliques más ni tensiones negativas, usa un divisor.\n\nEl muestreo va por "
                 "USB: unos cientos de muestras por segundo, repartidas entre los instrumentos "
                 "abiertos."))
