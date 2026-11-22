"""Búsqueda evolutiva de CÓDIGO (estilo AlphaEvolve) sobre una función del Pi, evaluada en el twin.

Un LLM (claude sonnet / codex, alternando) reescribe la función objetivo a partir de un padre del
archivo + retroalimentación (fallas, tiempos); cada hijo se mide en 48 carreras pareadas vs la base
p0 (mismas semillas). Si no agrega fallas y baja el tiempo, se promueve a las 288. Nada se exporta
ni se sube: los promovidos quedan en archivo.jsonl para revisión manual (réplica n7-12 a mano).

uso: python3 evo.py N_HIJOS   (corre en evo/; slots = worktrees wt-evo0/1)
"""
import json, os, random, re, subprocess, sys, time, statistics as st
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(HERE)
GH = "/Users/jesse/Documents/GitHub"
BASE_RUNS = f"{GH}/FoxRobotics-wt-perfil2.noindex/src/RASPI/cam/runs/latencia.noindex/p0"
SLOTS = [f"{GH}/FoxRobotics-wt-evo{k}.noindex" for k in (0, 1)]
FILE = "src/RASPI/cam/pure_pursuit/route_mode.py"
FUNC = os.environ.get("EVO_FUNC", "_profile_pwm")
PI_EXTRA = '{"ROUTE_FIX_LINE_LAG_FRAMES":5}'
ARCH = f"{HERE}/archivo.jsonl"
P_SLOT = int(os.environ.get("EVO_P", "7"))
FAIL_PEN = 1.5   # s por falla neta: una falla vale más que cualquier ganancia de tiempo


def stop(f):
    try:
        return json.loads([x for x in open(f, errors="ignore") if x.startswith("STOP ")][-1].split(" ", 2)[2])
    except Exception:
        return None


def res(root, n, s):
    t = stop(f"{root}/n{n}/s{s}.out")
    if t is None:
        return None
    ok = t.get("stop_reason") == "race_finished" and not t.get("collisions")
    return ok, float(t.get("total_time_s") or 0), t.get("stop_reason"), t.get("collisions")


def func_span(src, name):
    lines = src.split("\n")
    a = next(i for i, l in enumerate(lines) if re.match(rf"    def {name}\(", l))
    b = next(i for i in range(a + 1, len(lines)) if re.match(r"    (def |@)", lines[i]))
    while not lines[b - 1].strip():
        b -= 1
    return a, b, lines


def get_func(src):
    a, b, L = func_span(src, FUNC)
    return "\n".join(L[a:b])


def put_func(src, code):
    a, b, L = func_span(src, FUNC)
    return "\n".join(L[:a] + code.rstrip("\n").split("\n") + L[b:])


# Semillas de pantalla: 24 con menos holgura (más riesgo) + 24 al azar, fijas.
def pantalla():
    f = f"{HERE}/pantalla.txt"
    if os.path.exists(f):
        return [tuple(map(int, l.split())) for l in open(f)]
    rnd = random.Random(7)
    allk = [(n, s) for n in range(1, 7) for s in range(1, 49)]
    ok = [k for k in allk if (r := res(BASE_RUNS, *k)) and r[0]]
    rnd.shuffle(ok)
    # holgura mínima carrocería-señal desde porque.py (la de pareado)
    sys.path.insert(0, S)
    from pareado import una
    from multiprocessing import Pool
    with Pool(8) as p:
        hs = p.map(una, [f"{BASE_RUNS}/n{n}/s{s}" for n, s in ok])
    risk = [k for _, k in sorted(zip([h[2] if h else 999 for h in hs], ok))][:24]
    rest = [k for k in ok if k not in risk][:24]
    sel = sorted(risk + rest)
    open(f, "w").write("".join(f"{n} {s}\n" for n, s in sel))
    return sel


def bench(slot, tag, seeds):
    sf = f"{HERE}/seeds_{tag}.txt"
    open(sf, "w").write("".join(f"{n} {s}\n" for n, s in seeds))
    env = dict(os.environ, WT=slot, P=str(P_SLOT), SEEDS=sf)
    subprocess.run(["bash", f"{S}/w/bench.sh", tag, PI_EXTRA], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"{slot}/src/RASPI/cam/runs/latencia.noindex/{tag}"


def puntuar(root, seeds, base=None):
    base = base or BASE_RUNS
    reg, mej, dts, fallas = 0, 0, [], []
    for n, s in seeds:
        b, c = res(base, n, s), res(root, n, s)
        if b is None:
            continue
        if c is None:
            c = (False, 0.0, "sin_resultado", None)
        if b[0] and not c[0]:
            reg += 1
            fallas.append(f"n{n} s{s}: {c[2]} {str(c[3])[:160]}")
        elif c[0] and not b[0]:
            mej += 1
        if b[0] and c[0]:
            dts.append(c[1] - b[1])
    dt = st.median(dts) if dts else 9.9
    return {"reg": reg, "mej": mej, "dt": round(dt, 3), "dt_mean": round(st.mean(dts), 3) if dts else 9.9,
            "score": round(-dt - FAIL_PEN * (reg - mej), 3), "fallas": fallas[:8]}


def archivo():
    return [json.loads(l) for l in open(ARCH)] if os.path.exists(ARCH) else []


CONTEXTO = open(f"{HERE}/contexto.md").read()


def prompt(padre, arch, radical):
    top = sorted([a for a in arch if "score" in a], key=lambda a: -a["score"])[:6]
    hist = "\n".join(f"- id {a['id']} (padre {a.get('padre')}): score {a['score']} dt {a['dt']} s, fallas nuevas {a['reg']}, arregladas {a['mej']}. Idea: {a.get('idea','')}" for a in top)
    malos = "\n".join(f"- {a.get('idea','')[:140]}: {a.get('err') or ('reg %s dt %s' % (a.get('reg'), a.get('dt')))}" for a in arch[-14:] if a.get("score", 0) < -0.5)
    fb = "\n".join(padre.get("fallas") or []) or "(ninguna)"
    if padre.get("dt", 0) < -0.05 and padre.get("reg", 0):
        fb += f"\nEste padre AHORRA {-padre['dt']:.2f} s pero rompe {padre['reg']} carreras: conserva el ahorro y elimina esas fallas (protege solo donde fallan)."
    estilo = ("Propón algo RADICALMENTE distinto, aunque no sea intuitivo para un humano: otra forma de calcular el tope, "
              "otra física, otra estructura (p.ej. perfil hacia adelante+atrás, mezcla de velocidades por distancia, "
              "anticipar con la historia de tracking, usar la geometría real del paso entre señal y ruta). Sé creativo y concreto."
              if radical else
              "Haz UNA mejora enfocada sobre el padre (arreglar sus fallas o recortar tiempo donde sobra).")
    return f"""{CONTEXTO}

## Archivo (mejores hasta ahora; score = -(Δ mediana de tiempo, s) - {FAIL_PEN}·(fallas nuevas - arregladas))
{hist or '(vacío: solo la base)'}

## Intentos malos recientes (no repetir)
{malos or '(ninguno)'}

## Padre (id {padre['id']}, score {padre.get('score', 0)}); fallas nuevas del padre en la pantalla:
{fb}

```python
{padre['code']}
```

## Tarea
{estilo}
Responde EXACTAMENTE con:
IDEA: <una línea en español>
```python
<la función completa `{FUNC}` (misma firma, sangría de método de 4 espacios), sin nada más>
```"""


def _claude(p, cwd):
    return subprocess.run(["claude", "-p", "--model", "sonnet", "--tools", ""], input=p, cwd=cwd,
                          capture_output=True, text=True, timeout=900).stdout


def _codex(p, cwd):
    of = f"{HERE}/vacio/codex_{os.getpid()}_{time.time_ns()}.txt"   # archivo único: nunca releer una respuesta vieja
    subprocess.run(["codex", "exec", "--skip-git-repo-check", "-s", "read-only", "-o", of, "-"], input=p,
                   cwd=cwd, capture_output=True, text=True, timeout=900)
    out = open(of).read() if os.path.exists(of) else ""
    if os.path.exists(of):
        os.remove(of)
    return out


def mutar(p, k):
    cwd = f"{HERE}/vacio"
    try:
        out = _claude(p, cwd) if k % 2 == 0 else _codex(p, cwd)
        if "```python" not in out:   # límite de uso / error: el otro motor
            out = _codex(p, cwd) if k % 2 == 0 else _claude(p, cwd)
    except Exception as e:
        return None, f"error mutador {e}"
    m = re.search(r"```python\n(.*?)```", out, re.S)
    idea = (re.search(r"IDEA:\s*(.*)", out) or [None, "?"])[1].strip()[:300]
    if not m or f"def {FUNC}(" not in m.group(1):
        return None, idea
    code = m.group(1).rstrip()
    if not code.startswith("    def"):
        code = "\n".join("    " + l if l else l for l in code.split("\n"))
    return code, idea


def hijo(k, slot, padre, arch):
    radical = (k % 3 == 0)
    code, idea = mutar(prompt(padre, arch, radical), k)
    rec = {"id": k, "padre": padre["id"], "idea": idea, "radical": radical, "t0": time.time()}
    if code is None:
        rec.update(score=-9, reg=0, mej=0, dt=9.9, err="sin código")
        return rec
    f = f"{slot}/{FILE}"
    subprocess.run(["git", "-C", slot, "checkout", "-q", "--", FILE])
    src0 = open(f).read()
    open(f, "w").write(put_func(src0, code))
    if subprocess.run([sys.executable, "-m", "py_compile", f], capture_output=True).returncode:
        rec.update(score=-9, reg=0, mej=0, dt=9.9, err="no compila", code=code)
        return rec
    tag = f"e{k}"
    root = bench(slot, tag, SEEDS)
    rec.update(puntuar(root, SEEDS), code=code)
    if rec["reg"] - rec["mej"] <= 0 and rec["dt"] <= -0.08:
        allk = [(n, s) for n in range(1, 7) for s in range(1, 49)]
        bench(slot, tag, allk)
        full = puntuar(root, allk)
        rec["full"] = {k2: full[k2] for k2 in ("reg", "mej", "dt", "dt_mean")}
        rec["promovido"] = full["reg"] - full["mej"] <= 0 and full["dt"] < 0
        if not rec["promovido"]:
            subprocess.run(["rm", "-rf", root])
    else:
        subprocess.run(["rm", "-rf", root])
    subprocess.run(["git", "-C", slot, "checkout", "-q", "--", FILE])
    return rec


def elegir(arch, base):
    vivos = [a for a in arch if a.get("score", -9) > -9 and "code" in a]
    r = random.random()
    rapidos = sorted([a for a in vivos if a.get("dt", 9) < -0.05], key=lambda a: a["dt"])[:4]
    if not vivos or r < 0.15:
        return base
    if rapidos and r < 0.55:
        return random.choice(rapidos)   # rápido pero con fallas: el hijo debe arreglarlas sin perder el ahorro
    return random.choice(sorted(vivos, key=lambda a: -a["score"])[:5])


SEEDS = None


def main():
    global SEEDS
    nh = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    SEEDS = pantalla()
    base_src = subprocess.run(["git", "-C", SLOTS[0], "show", f"HEAD:{FILE}"], capture_output=True, text=True).stdout
    base = {"id": 0, "code": get_func(base_src), "score": 0.0, "fallas": []}
    arch = archivo()
    k0 = max([a["id"] for a in arch] + [0]) + 1
    lock_k = iter(range(k0, k0 + nh))

    def worker(slot):
        for k in lock_k:
            r = hijo(k, slot, elegir(archivo(), base), archivo())
            with open(ARCH, "a") as fh:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"[{time.strftime('%H:%M')}] e{k} score {r.get('score')} reg {r.get('reg')} mej {r.get('mej')} dt {r.get('dt')} "
                  f"{'PROMOVIDO ' + str(r.get('full')) if r.get('promovido') else ''} | {r.get('idea','')[:90]}", flush=True)

    with ThreadPoolExecutor(len(SLOTS)) as ex:
        list(ex.map(worker, SLOTS))


if __name__ == "__main__":
    main()
