# evo: búsqueda evolutiva de código con grafo de agentes (twin)

- `grafo.py N`: analista (codex) → mutador (codex 2/3, claude 1/3; si uno no responde, el otro) → compuerta
  estática → crítico (codex) → 6 semillas (corta no-ops) → 48 pareadas vs p0 → 288 → réplica ruidos 7-12 vs b712.
  Reflexión cada 8 hijos reescribe `lecciones.md`. Nada se exporta ni se sube solo.
- `evo.py`: evaluador, prompts y selección (40% padres rápidos con fallas, para que el hijo las arregle).
- Función mutada: `RouteMode._profile_pwm`. Base: fox/twin-iter d771e912 + ROUTE_FIX_LINE_LAG_FRAMES 5.
- Rutas absolutas de la Mac (scratchpad, worktrees wt-evo0/1, base p0 en wt-perfil2); `lib/` son copias de
  bench.sh / pareado.py / porque.py del scratchpad. Ajustar S/GH en evo.py si se mueve.
- Estado al pausar (2026-11-22): ~19 hijos válidos, ninguno gana. Mejor pista: e18 (vuelta 1, mezcla de κ en vez
  de máx simétrico) −0.30 s con 4 fallas; e10 −0.012 s con 3 fallas. Lo de subir A_LAT o soltar el frenado
  agrega fallas; muchos cambios son no-op porque el perfil no es la capa que manda.
