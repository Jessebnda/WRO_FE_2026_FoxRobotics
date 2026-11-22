"""Por qué choca con una señal: falla vs la MISMA semilla que pasa, con la carrocería real (176x125).

uso: porque.py FALLA_DIR/nN/sS PASA_DIR/nN/sS
Holgura = distancia carrocería-cubo de la señal (50 mm). Compara, a igual distancia recorrida, el
último 1.5 s antes del choque: holgura, parte del carro que se acerca, velocidad, servo, desvío lateral
respecto a la carrera que pasa y adelanto de tiempo.
"""
import csv, json, math, re, sys
import numpy as np

L, W, RO, HALF = 176.0, 125.0, 21.8, 25.0
SERVO_C = 90.0
# perímetro del carro en coordenadas locales (derecha, adelante) con etiqueta
_pts, _lab = [], []
for f in np.linspace(-W / 2, W / 2, 32):
    _pts += [(f, L - RO), (f, -RO)]; _lab += ["frente", "cola"]
for a in np.linspace(-RO, L - RO, 45):
    _pts += [(W / 2, a), (-W / 2, a)]; _lab += ["lado der" if a < 60 else "esq. del. der", "lado izq" if a < 60 else "esq. del. izq"]
PTS = np.array(_pts); LAB = np.array(_lab)


def traza(d):
    R = list(csv.DictReader(open(d + "/trace.csv")))
    tc, cur = [], 0
    for r in R:
        m = re.search(r"tc=(\d+)", r["ack"] or "")
        cur = int(m.group(1)) if m else cur
        tc.append(cur)
    f = lambda k: np.array([float(r[k] or 0) for r in R])
    x, y = f("x"), f("y")
    s = np.r_[0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
    return dict(t=f("t"), x=x, y=y, h=f("heading"), v=f("speed_mm_s"), sv=f("servo"), pwm=f("motor_pwm"), s=s, tc=np.array(tc))


def holgura(T, i, sx, sy):
    h = math.radians(T["h"][i]); sh, ch = math.sin(h), math.cos(h)
    wx = T["x"][i] + PTS[:, 1] * sh + PTS[:, 0] * ch
    wy = T["y"][i] + PTS[:, 1] * ch - PTS[:, 0] * sh
    dx = np.maximum(np.abs(wx - sx) - HALF, 0); dy = np.maximum(np.abs(wy - sy) - HALF, 0)
    d = np.hypot(dx, dy); j = int(np.argmin(d))
    return d[j], LAB[j]


def main():
    fd, pd = sys.argv[1], sys.argv[2]
    F, P = traza(fd), traza(pd)
    st = json.loads([x for x in open(fd.rstrip("/") + ".out", errors="ignore") if x.startswith("STOP ")][-1].split(" ", 2)[2])
    col = (st.get("collisions") or [{}])[0]
    cause, tcol = col.get("cause", "?"), col.get("t", F["t"][-1])
    nm = cause.replace("señal ", "")
    S = {f"{m[1]} {m[2]}": (int(m[3]), int(m[4])) for m in re.finditer(r"(Red|Green) (\S+) \((-?\d+),(-?\d+)\)", open(fd + "/field.txt").read())}
    if nm not in S:
        print(f"{cause}: no es señal"); return
    sx, sy = S[nm]
    k = int(np.searchsorted(F["t"], tcol)) - 1
    print(f"FALLA {cause} @ {tcol:.2f}s tc={F['tc'][k]} v={F['v'][k]:.0f} servo={F['sv'][k]:.0f}")
    pas = [(holgura(P, i, sx, sy)[0], i) for i in range(len(P["t"]))]
    # la pasada correspondiente: la de P más cercana a la misma distancia recorrida
    sk = F["s"][k]
    win = [i for i in range(len(P["t"])) if abs(P["s"][i] - sk) < 600]
    hp, ip = min((holgura(P, i, sx, sy)[0], i) for i in win)
    print(f"  la que pasa, en esa misma pasada: holgura mínima {hp:.0f} mm ({holgura(P, ip, sx, sy)[1]}) v={P['v'][ip]:.0f} servo={P['sv'][ip]:.0f} tc={P['tc'][ip]}")
    print("  t-antes | falla: holg  parte          v    servo | pasa: holg   v    servo | desvío lat  adelanto")
    for dt in (1.5, 1.0, 0.7, 0.5, 0.3, 0.15, 0.0):
        i = int(np.searchsorted(F["t"], tcol - dt)) - 1
        j = int(np.searchsorted(P["s"], F["s"][i]))
        j = min(j, len(P["t"]) - 1)
        hf, pf = holgura(F, i, sx, sy); hq, _ = holgura(P, j, sx, sy)
        # desvío lateral: proyección de (F-P) sobre la normal del rumbo de P
        hh = math.radians(P["h"][j]); nx, ny = math.cos(hh), -math.sin(hh)   # derecha del carro
        lat = (F["x"][i] - P["x"][j]) * nx + (F["y"][i] - P["y"][j]) * ny
        adel = (P["t"][j] - P["t"][0]) - (F["t"][i] - F["t"][0])
        print(f"  {dt:5.2f} s | {hf:5.0f} {pf:14s} {F['v'][i]:5.0f} {F['sv'][i]:5.0f} | {hq:5.0f} {P['v'][j]:5.0f} {P['sv'][j]:5.0f} | {lat:+6.0f} mm {adel:+.2f} s")


if __name__ == "__main__":
    main()
