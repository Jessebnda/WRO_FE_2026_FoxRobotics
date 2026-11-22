"""Grafo de agentes sobre evo.py (graph engineering: flujo explícito en código, nodos LLM solo donde hay juicio).

  padre ─► ANALISTA (codex, lee trazas) ─► MUTADOR (codex 2/3, claude 1/3) ─► compuerta estática
        ─► CRÍTICO (codex: noop / trampa del twin / ok) ─► EVALUADOR 48 pareadas ─► [prometedor] 288
        ─► VALIDADOR ruidos 7-12 vs base b712 ─► candidato para revisión humana (no se sube nada)
  cada 8 hijos: REFLEXIÓN (codex) reescribe lecciones.md, que entra al prompt del mutador.

Estado compartido: archivo.jsonl, lecciones.md, nodos/<k>_<nodo>.txt (lo que dijo cada nodo).
uso: python grafo.py N_HIJOS
"""
import json, os, random, re, shutil, subprocess, sys, time, threading
from concurrent.futures import ThreadPoolExecutor
import evo
from evo import HERE, S, SLOTS, FILE, FUNC, ARCH, res, puntuar, bench, get_func, put_func, archivo

NOD = f"{HERE}/nodos"; os.makedirs(NOD, exist_ok=True)
KEEP = f"{HERE}/fallas"; os.makedirs(KEEP, exist_ok=True)
LECC = f"{HERE}/lecciones.md"
B712 = f"{SLOTS[0]}/src/RASPI/cam/runs/latencia.noindex/b712"
N712 = [(n, s) for n in range(7, 13) for s in range(1, 49)]
ALL = [(n, s) for n in range(1, 7) for s in range(1, 49)]
lock = threading.Lock()


def llm(nodo, k, p, motor="codex", cwd=None):
    cwd = cwd or f"{HERE}/vacio"
    of = f"{NOD}/{k}_{nodo}.txt"
    try:
        out = evo._codex(p, cwd) if motor == "codex" else ""
        if not out.strip():                       # codex sin cuota o sin respuesta: claude
            out = evo._claude(p, cwd)
        open(of, "w").write(out)
        return out
    except Exception as e:
        return f"ERROR {e}"


def js(txt):
    m = re.findall(r"\{.*\}", txt or "", re.S)
    for c in reversed(m):
        try:
            return json.loads(c)
        except Exception:
            pass
    return {}


# ---------- nodo ANALISTA ----------
DIAG = {}


def analista(k, padre):
    if padre["id"] in DIAG:
        return DIAG[padre["id"]]
    base_dir = f"{SLOTS[0]}/../FoxRobotics-wt-perfil2.noindex/src/RASPI/cam/runs/latencia.noindex/p0"
    fd = f"{KEEP}/e{padre['id']}"
    if padre["id"] and os.path.isdir(fd) and os.listdir(fd):
        foco = (f"El padre FALLÓ en estas carreras (dirs del padre en {fd}/<nN_sS>/, mismas semillas en la base "
                f"{base_dir}/nN/sS/):\n" + "\n".join(padre.get("fallas") or []) +
                "\nEncuentra el MECANISMO de la falla (qué parte del tope dejó pasar demasiada velocidad, dónde).")
    else:
        foco = (f"Analiza la base ({base_dir}/n1..n6/sS/, mira 4-6 carreras) y di dónde el tope de velocidad "
                "deja tiempo sobre la mesa en vueltas 1-3 (frenadas innecesarias, zonas lentas sin señal cerca, "
                "aceleración tardía al salir de curva).")
    p = f"""{evo.CONTEXTO}
Eres el ANALISTA de un grafo de agentes. Puedes leer archivos y correr python de solo lectura.
trace.csv: t,x,y,heading,speed_mm_s,motor_pwm,servo,ds_mm,ack,... (cada cuadro); pi.log tiene rv= (tope) y tc;
field.txt las señales; el .out tiene la línea STOP con stop_reason y collisions. Herramientas: {S}/porque.py, {S}/tiempos.py.
{foco}
Código actual de la función (padre):
```python
{padre['code'][:6000]}
```
Responde con un JSON: {{"mecanismo": "...", "donde": "...", "propuesta": "cambio de algoritmo concreto"}} (máx 150 palabras)."""
    d = js(llm("analista", k, p, cwd=f"{SLOTS[0]}/src/RASPI/cam"))
    DIAG[padre["id"]] = d
    return d


# ---------- nodo CRÍTICO ----------
PROHIB = re.compile(r"\b(import |open\(|print\(|exec\(|eval\(|subprocess|os\.)")


def critico(k, padre, code, idea):
    if PROHIB.search(code):
        return {"veredicto": "rechazo", "razon": "E/S o import prohibido"}
    if code.strip() == padre["code"].strip():
        return {"veredicto": "noop", "razon": "idéntico al padre"}
    p = f"""{evo.CONTEXTO}
Eres el CRÍTICO del grafo. Compara padre e hijo del método `{FUNC}`. Idea del hijo: {idea}
Padre:
```python
{padre['code']}
```
Hijo:
```python
{code}
```
Decide UNO: "noop" (el cambio nunca se activa o no altera el resultado con los valores actuales),
"trampa" (explota algo que solo existe en el simulador o es físicamente imposible en el carro real, o cambia
salida/U/parking), "bug" (error claro: excepción posible, unidades, índices), u "ok".
Responde JSON: {{"veredicto": "...", "razon": "una línea"}}"""
    return js(llm("critico", k, p)) or {"veredicto": "ok", "razon": "crítico sin respuesta"}


# ---------- nodo REFLEXIÓN ----------
def reflexion(k):
    arch = archivo()
    filas = "\n".join(f"e{a['id']}<-e{a.get('padre')} score {a.get('score')} reg {a.get('reg')} dt {a.get('dt')} "
                      f"{a.get('err','')} {('CRIT:' + a['critica']) if a.get('critica') else ''} | {a.get('idea','')}" for a in arch)
    prev = open(LECC).read() if os.path.exists(LECC) else ""
    p = f"""{evo.CONTEXTO}
Eres el nodo de REFLEXIÓN de una búsqueda evolutiva de código. Historial completo:
{filas}
Lecciones previas:
{prev}
Reescribe las lecciones (máx 25 líneas, español): qué direcciones bajan tiempo sin fallas, cuáles fallan y POR
QUÉ (mecanismo), qué no se ha explorado y vale la pena (sé audaz: ideas no obvias), y errores repetidos del mutador.
Solo el texto de las lecciones."""
    txt = llm("reflexion", k, p)
    if txt and not txt.startswith("ERROR"):
        open(LECC, "w").write(txt.strip() + "\n")


def guardar_fallas(k, root, rec):
    d = f"{KEEP}/e{k}"
    for f in rec.get("fallas") or []:
        m = re.match(r"n(\d+) s(\d+)", f)
        if m and os.path.isdir(f"{root}/n{m[1]}/s{m[2]}"):
            shutil.copytree(f"{root}/n{m[1]}/s{m[2]}", f"{d}/n{m[1]}_s{m[2]}", dirs_exist_ok=True)
            shutil.copy(f"{root}/n{m[1]}/s{m[2]}.out", f"{d}/n{m[1]}_s{m[2]}.out")


def hijo(k, slot, padre):
    rec = {"id": k, "padre": padre["id"], "t0": time.time()}
    diag = analista(k, padre)
    arch = archivo()
    lecc = open(LECC).read() if os.path.exists(LECC) else ""
    p = evo.prompt(padre, arch, radical=(k % 3 == 0))
    p = p.replace("## Tarea", f"## Diagnóstico del ANALISTA\n{json.dumps(diag, ensure_ascii=False)}\n\n## Lecciones acumuladas\n{lecc}\n\n## Tarea")
    code, idea = evo.mutar(p, 1 if k % 3 else 0)     # 1 = codex, 0 = claude: codex 2 de cada 3
    rec.update(idea=idea, radical=(k % 3 == 0), diag_padre=diag)
    if code is None:
        rec.update(score=-9, reg=0, mej=0, dt=9.9, err="sin código")
        return rec
    if any(a.get("idea", "")[:60] == idea[:60] for a in arch):
        rec.update(score=-9, reg=0, mej=0, dt=9.9, err="idea repetida")
        return rec
    cr = critico(k, padre, code, idea)
    rec["critica"] = f"{cr.get('veredicto')}: {cr.get('razon', '')}"[:200]
    if cr.get("veredicto") in ("noop", "trampa", "bug", "rechazo"):
        rec.update(score=-9, reg=0, mej=0, dt=9.9, err=f"crítico {cr.get('veredicto')}", code=code)
        return rec
    f = f"{slot}/{FILE}"
    subprocess.run(["git", "-C", slot, "checkout", "-q", "--", FILE])
    src0 = open(f).read()
    open(f, "w").write(put_func(src0, code))
    if subprocess.run([sys.executable, "-m", "py_compile", f], capture_output=True).returncode:
        rec.update(score=-9, reg=0, mej=0, dt=9.9, err="no compila", code=code)
        subprocess.run(["git", "-C", slot, "checkout", "-q", "--", FILE])
        return rec
    tag = f"e{k}"
    pre = evo.SEEDS[::8]   # 6 semillas: si nada cambia en ninguna, es no-op real (no gastar las otras 42)
    root = bench(slot, tag, pre)
    if all((b := res(evo.BASE_RUNS, n, s)) and (c := res(root, n, s)) and abs(b[1] - c[1]) < 1e-6 for n, s in pre):
        rec.update(score=-9, reg=0, mej=0, dt=0.0, err="noop medido (6 semillas idénticas)", code=code)
        subprocess.run(["rm", "-rf", root]); subprocess.run(["git", "-C", slot, "checkout", "-q", "--", FILE])
        return rec
    root = bench(slot, tag, evo.SEEDS)
    rec.update(puntuar(root, evo.SEEDS), code=code)
    if rec["reg"] - rec["mej"] <= 0 and rec["dt"] <= -0.08:
        bench(slot, tag, ALL)
        full = puntuar(root, ALL)
        rec["full"] = {x: full[x] for x in ("reg", "mej", "dt", "dt_mean")}
        if full["reg"] - full["mej"] <= 0 and full["dt"] < 0:
            # VALIDADOR: ruidos frescos 7-12 contra la base b712
            bench(slot, tag, N712)
            v = puntuar(root, N712, B712)
            rec["valid712"] = {x: v[x] for x in ("reg", "mej", "dt", "dt_mean")}
            rec["promovido"] = v["reg"] - v["mej"] <= 0 and v["dt"] < 0
    guardar_fallas(k, root, rec)
    if not rec.get("promovido"):
        subprocess.run(["rm", "-rf", root])
    subprocess.run(["git", "-C", slot, "checkout", "-q", "--", FILE])
    return rec


def main():
    nh = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    evo.SEEDS = evo.pantalla()
    if not all(res(B712, n, s) for n, s in N712[::47]):
        subprocess.run(["git", "-C", SLOTS[0], "checkout", "-q", "--", FILE])
        bench(SLOTS[0], "b712", N712)    # base en ruidos frescos, una vez
    base_src = subprocess.run(["git", "-C", SLOTS[0], "show", f"HEAD:{FILE}"], capture_output=True, text=True).stdout
    base = {"id": 0, "code": get_func(base_src), "score": 0.0, "fallas": []}
    k0 = max([a["id"] for a in archivo()] + [0]) + 1
    ks = iter(range(k0, k0 + nh))

    def worker(slot):
        for k in ks:
            padre = evo.elegir(archivo(), base)
            try:
                r = hijo(k, slot, padre)
            except Exception as e:
                import traceback; traceback.print_exc()
                subprocess.run(["git", "-C", slot, "checkout", "-q", "--", FILE])
                r = {"id": k, "padre": padre["id"], "score": -9, "reg": 0, "mej": 0, "dt": 9.9, "err": f"excepción {e!r}"[:200]}
            with lock:
                with open(ARCH, "a") as fh:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"[{time.strftime('%H:%M')}] e{k}<-e{r['padre']} score {r.get('score')} reg {r.get('reg')} mej {r.get('mej')} "
                  f"dt {r.get('dt')} {r.get('err', '')} {('FULL ' + str(r['full'])) if r.get('full') else ''} "
                  f"{('V712 ' + str(r['valid712'])) if r.get('valid712') else ''} {'PROMOVIDO' if r.get('promovido') else ''} "
                  f"| {r.get('idea', '')[:80]}", flush=True)
            if k % 8 == 0:
                reflexion(k)
                print(f"[{time.strftime('%H:%M')}] reflexión e{k}: lecciones.md actualizado", flush=True)

    with ThreadPoolExecutor(len(SLOTS)) as ex:
        list(ex.map(worker, SLOTS))


if __name__ == "__main__":
    main()
