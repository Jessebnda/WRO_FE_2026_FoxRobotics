#!/bin/bash
# uso: WT=<worktree> [P=6] [SEEDS=archivo "nz s"] [FWX='"K":"v"'] bench.sh tag 'json_pi_extra'
#  default 288 carreras (n1-n6 x s1-48), TWIN_COST_FIJO=1, base carrera_bench.json del worktree.
tag=$1; ex=${2:-'{}'}
cd ${WT:?}/src/RASPI/cam || exit 1
export FOX_PY=/Users/jesse/Documents/GitHub/FoxRobotics/.venv/bin/python TWIN_VBAT=12.5 TWIN_COST_FIRST=1.95 TWIN_COST_FIJO=1
export TWIN_PI_EXTRA="$ex" TWIN_FW_OVER="{${FWX}}"
U=pure_pursuit/twin/tools/latencia/uno.sh
{ if [ -n "$SEEDS" ]; then cat "$SEEDS"; else for nz in 1 2 3 4 5 6; do for s in $(seq 1 48); do echo "$nz $s"; done; done; fi; } |
  xargs -P ${P:-6} -L 1 bash -c "$U $tag 4.28 5.8 \$0 \$1"
echo FIN $tag
