"""Comparación PAREADA de dos bancos (misma semilla de ruido y campo) + holgura mínima a señales.

uso: pareado.py RUNS_DIR BASE CAND      (RUNS_DIR = .../runs/latencia.noindex)
Imprime: pares discordantes (cand falla & base pasa / al revés) y p de McNemar exacto, diferencia
pareada de tiempo (mediana e IC 95% bootstrap) sobre las que pasan en ambas, p5/p1 de la holgura
mínima carrocería-señal y casi-fallas (<10 mm) en las que pasan.
"""
import json, math, os, re, sys
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from porque import traza, holgura


def stop(f):
    try:
        st = json.loads([x for x in open(f, errors="ignore") if x.startswith("STOP ")][-1].split(" ", 2)[2])
    except Exception:
        return None
    return st


def una(args):
    d = args
    st = stop(d + ".out")
    if st is None or not os.path.exists(d + "/trace.csv"):
        return None
    ok = st.get("stop_reason") == "race_finished" and not st.get("collisions")
    # summ3 también cuenta "fuera" del cajón; se usa su criterio si está
    t = float(st.get("total_time_s") or 0)
    try:
        T = traza(d)
        S = [(int(m[3]), int(m[4])) for m in re.finditer(r"(Red|Green) (\S+) \((-?\d+),(-?\d+)\)", open(d + "/field.txt").read())]
        hm = min(holgura(T, i, sx, sy)[0] for sx, sy in S for i in range(0, len(T["t"]), 3)) if S else 999.0
    except Exception:
        hm = float("nan")
    return ok, t, hm


def banco(root, tag):
    keys = [(n, s) for n in range(1, 7) for s in range(1, 49)]
    with Pool(8) as p:
        r = p.map(una, [f"{root}/{tag}/n{n}/s{s}" for n, s in keys])
    return dict(zip(keys, r))


def main():
    root, a, b = sys.argv[1:4]
    A, B = banco(root, a), banco(root, b)
    ks = [k for k in A if A[k] and B[k]]
    fa = sum(1 for k in ks if not B[k][0] and A[k][0])
    fb = sum(1 for k in ks if B[k][0] and not A[k][0])
    nd = fa + fb
    p = min(1.0, 2 * sum(math.comb(nd, i) for i in range(0, min(fa, fb) + 1)) / 2 ** nd) if nd else 1.0
    print(f"{b} vs {a}: n={len(ks)}  ok {sum(B[k][0] for k in ks)} vs {sum(A[k][0] for k in ks)}  "
          f"empeora {fa} / mejora {fb}  McNemar p={p:.3f}")
    both = [k for k in ks if A[k][0] and B[k][0]]
    dt = np.array([B[k][1] - A[k][1] for k in both])
    rng = np.random.default_rng(0)
    bs = [np.median(rng.choice(dt, len(dt))) for _ in range(2000)]
    print(f"  tiempo pareado (ambas pasan, n={len(dt)}): mediana {np.median(dt):+.2f} s  IC95 [{np.percentile(bs, 2.5):+.2f}, {np.percentile(bs, 97.5):+.2f}]")
    for nm, X in ((a, A), (b, B)):
        h = np.array([X[k][2] for k in ks if X[k][0] and not math.isnan(X[k][2])])
        print(f"  {nm:10s} holgura min (pasan): p1 {np.percentile(h, 1):.0f}  p5 {np.percentile(h, 5):.0f}  mediana {np.median(h):.0f} mm  casi-fallas<10mm {int((h < 10).sum())}")
    print("  empeoran:", " ".join(f"n{n}s{s}" for (n, s) in ks if A[(n, s)][0] and not B[(n, s)][0]))


if __name__ == "__main__":
    main()
