# l1r — primera vuelta

El experimento parte de `b1f2e7ed`. La base y el candidato del banco principal ejecutan el mismo árbol `4886b2a`. La base conserva apagados los tres flags nuevos.

- `ROUTE_L1_DRAW_INFERENCE` enumera los sorteos legales compatibles con confirmaciones y vacíos. A partir de tres rectas con confirmaciones, puede fijar el lado cuando solo queda un color posible o eliminar un asiento imposible. Si la evidencia no admite un sorteo o la ruta inferida es inviable, conserva el plan previo a la inferencia.
- `ROUTE_L1_PATH_BRAKE` usa la huella barrida en el horizonte de frenado con reserva de seguimiento. Requiere una ruta factible ya subida al ESP y error lateral inferior a 30 mm. Conserva el freno para asientos cuya detección aún podría exigir cambiar de lado.
- `ROUTE_L1_LOCK_PASS_SIDE` retiene en V2–V3 un lado confirmado y recorrido en V1 cuando el mapa pierde el asiento. Una nueva confirmación tiene prioridad.

## Banco

`latencia/uno.sh`, FF 4.28 y FD 5.8. Semillas 1–48 por cada ruido 1–6. Ambos brazos usan exactamente estas variables.

```bash
export TWIN_TOF_SHORT_K=0.5 TWIN_MOTOR_CURVA_REAL=1 TWIN_CAMERA_FROM_CALIB=1
export TWIN_MOTOR_REAL=1 TWIN_VBAT=11.5 TWIN_COST_FIJO=1 TWIN_COST_FIRST=1.95
export TWIN_LENS_CALIB=pure_pursuit/lens_calib.npz
export TWIN_FW_OVER='{"MOTOR_CURVE_LIVE":"false"}'
# Base
export TWIN_PI_EXTRA='{"ROUTE_MOTOR_CURVE_LIVE":false}'
# Candidato
export TWIN_PI_EXTRA='{"ROUTE_MOTOR_CURVE_LIVE":false,"ROUTE_L1_DRAW_INFERENCE":true,"ROUTE_L1_PATH_BRAKE":true,"ROUTE_L1_LOCK_PASS_SIDE":true}'
```

Una carrera limpia acaba con 12 giros y el carro dentro del cajón, con la tolerancia de 5 mm de `optimizar_park.py`. Cuentan como fallas los contactos de pared aun si el banco los registra y continúa, y los contactos con señales. Las medias y medianas usan carreras limpias. Los deltas pareados usan los mismos casos limpios en ambos brazos.

El primer cribado (`9d615bd`) probó quitar la atracción a asientos ambiguos y soltar antes el freno. Introdujo contactos en n1/s3, n1/s4 y n1/s6. El candidato principal conserva la atracción y la reserva de la DP base, y mantiene fuera del localizador ToF las hipótesis del sorteo.

## Resultado

**No aceptado.**

| Métrica | Base | Candidato |
| --- | ---: | ---: |
| Corridas con resultado | 288 | 288 |
| Carreras terminadas | 281 | 233 |
| Limpias | 279 | 231 |
| Mejor total (s) | 31.997 | 31.994 |
| Media total (s) | 36.733 | 37.008 |
| Mediana total (s) | 36.364 | 36.809 |
| V1 media (s) | 12.342 | 12.416 |
| V1 mediana (s) | 12.300 | 12.326 |

En 224 pares limpios, el delta candidato menos base fue **-0.021 s en V1** y **+0.141 s en total**.

Hubo 55 regresiones y 7 recuperaciones en el pareado.

De las regresiones, 21 ocurrieron con cuatro giros completados y 16 con los doce giros completados. El banco compara los tres flags juntos, por lo que no atribuye esas fallas a un flag individual. Los tres quedan apagados.

### Fallas

**Base**

- **n1** — `s21` (stuck (tc=12)), `s23` (sobresale 7.6 mm del cajón (tc=12))
- **n2** — `s20` (stuck (tc=12)), `s26` (cajón magenta (tc=12))
- **n3** — `s3` (señal Green S/T1 (tc=3)), `s12` (sobresale 5.1 mm del cajón (tc=12))
- **n4** — sin fallas
- **n5** — `s26` (stuck (tc=12)), `s36` (señal Green S/T1 (tc=1))
- **n6** — `s21` (stuck (tc=12))

**Candidato**

- **n1** — `s11` (pared (tc=4)), `s14` (cajón magenta (tc=12)), `s19` (cajón magenta (tc=12)), `s24` (señal Red N/T1 (tc=3)), `s25` (stuck (tc=12)), `s33` (pared (tc=4)), `s40` (pared (tc=12)), `s43` (pared (tc=4)), `s44` (señal Green W/T2 (tc=12)), `s48` (pared (tc=4))
- **n2** — `s4` (stuck (tc=12)), `s5` (señal Green S/T1 (tc=12)), `s11` (pared (tc=4)), `s20` (cajón magenta (tc=12)), `s24` (pared (tc=8)), `s25` (pared (tc=12)), `s33` (pared (tc=4)), `s40` (pared (tc=11)), `s43` (pared (tc=4)), `s44` (pared (tc=11)), `s48` (pared (tc=4))
- **n3** — `s11` (pared (tc=4)), `s24` (pared (tc=6)), `s27` (señal Red S/T4 (tc=6)), `s33` (pared (tc=4)), `s40` (pared (tc=11)), `s43` (pared (tc=4)), `s44` (pared (tc=11)), `s48` (pared (tc=4))
- **n4** — `s7` (sobresale 6.4 mm del cajón (tc=12)), `s11` (pared (tc=4)), `s24` (pared (tc=11)), `s25` (pared (tc=12)), `s29` (sobresale 6.5 mm del cajón (tc=12)), `s33` (pared (tc=4)), `s40` (pared (tc=11)), `s43` (pared (tc=4)), `s44` (señal Green W/T2 (tc=12))
- **n5** — `s6` (cajón magenta (tc=12)), `s11` (pared (tc=4)), `s24` (pared (tc=6)), `s25` (pared (tc=12)), `s33` (pared (tc=4)), `s36` (señal Green S/T1 (tc=1)), `s40` (pared (tc=11)), `s43` (pared (tc=3)), `s44` (pared (tc=11))
- **n6** — `s4` (señal Red N/T2 (tc=5)), `s5` (señal Green S/T1 (tc=12)), `s11` (pared (tc=4)), `s23` (pared (tc=11)), `s24` (pared (tc=6)), `s33` (pared (tc=4)), `s40` (señal Green S/T2 (tc=12)), `s43` (pared (tc=4)), `s44` (pared (tc=11)), `s48` (pared (tc=4))

Nueve tests dirigidos pasaron. Las 74 primeras corridas de control con los flags apagados coincidieron con el árbol original en tiempos, giros y contactos.

Los registros `STOP` y `COSTO`, las trazas y el JSON de resultados están en `/workspace/l1r-bank`.
