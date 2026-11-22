# Contexto: tope de velocidad de un carro autónomo (WRO Future Engineers), evaluado en un simulador

Carro 1:10 aprox. (Ackermann, ancho ~150 mm), pista cuadrada 3x3 m con isla central 1x1 m (INNER_HALF_MM=500),
pasillos de ~1 m. Da 3 vueltas esquivando señales (pilares rojo/verde, ~50 mm de lado, en asientos fijos
de cada recta) y se estaciona. Tocar pared o señal = falla (lo peor que puede pasar). Objetivo: menos
tiempo total sin agregar fallas.

Arquitectura: una Raspberry Pi planea una ruta (DP) y la sube al ESP32, que la sigue con pure pursuit y
un lazo de velocidad (retraso ~0.1 s + filtro de 1er orden ~0.2 s). La Pi corre a ~40 fps y en CADA cuadro
llama a la función de abajo, que devuelve UN tope de PWM (escalar) para el próximo instante; el ESP lo
sigue. Velocidad ≈ K·(pwm − pwm0) mm/s, K=3.639, pwm0=18.7; PWM máximo 458 (~1600 mm/s nominal, en la
práctica ~830 mm/s por el motor). Ese tope solo puede BAJAR la velocidad que piden otras capas.

Datos disponibles dentro del método (self):
- self.follower.route: arrays r.x, r.y (mm, mundo, origen centro pista), r.s (abscisa acumulada mm),
  r.kappa (curvatura 1/mm, + = izquierda), r.length_mm (anillo cerrado, índices módulo n).
- self.follower.i: índice actual del carro en la ruta. self._tc_max: cuenta de tramos (4 tramos por vuelta:
  tc 0 salida, 1-3 vuelta 1 cuando aún no conoce todas las señales, 4-7 vuelta 2, 8-11 vuelta 3, ≥11 final al cajón).
- signs: np.array (k,2) mm de las señales conocidas (o None). self._unk_pts: asientos sin resolver.
- self.fixed: ya ubicó el cajón de estacionamiento. C: módulo de config (claves ROUTE_PROFILE_*, ROUTE_L23_*,
  ROUTE_L1_*; usa getattr(C, X, default) para claves nuevas o constantes en la propia función).
- Helpers del módulo ya importados: np, _pursuit_kappa(r, j, lookahead_mm, left_factor), INNER_HALF_MM.
- Valores actuales: A_LAT 2767 (vuelta1) / 3200 (vueltas 2-3) mm/s², A_BRAKE 3004 / 900 (2-3), LATENCY 0.16 s,
  MIN_PWM 216, L1_MIN_PWM 235, SIGN_MM 192, SIGN_NEAR_MM 172, SIGN_TIGHT_PWM 101, BRAKE_FF_S 0.04.
  l1=True en tc 1-3, l23=True en tc 4-11, lap2=True en tc 4-7. Fuera de eso (salida, U, parking) debe
  comportarse como la base (no cambies esas fases; si l1/l23 son False, deja el resultado de la base).

Lo que sabemos: la forma de la ruta casi no cambia la velocidad; manda este perfil (a_lat, pisos, zonas
de señal). Las vueltas 2-3 duran ~7.3 s cada una, la vuelta 1 ~11 s. Desviación típica de seguimiento en
entrada de curva 40-110 mm hacia adentro, crece con la velocidad. Las fallas típicas: rozar la señal
interior al salir de una curva o la pared exterior en curva rápida.

Restricciones duras: misma firma, devuelve int o None, nada de E/S ni estado global nuevo fuera de
atributos self._evo_* (puedes guardar historia en self si la inicializas con getattr). Debe ser rápido
(<1 ms, numpy vectorizado). Se evalúa en 48 carreras simuladas con ruido, pareadas contra la base.

Aviso del grafo: muchos hijos salen no-op exacto porque este tope NO es la capa que manda en ese momento
(otras capas: tope de subida de ruta, swap, plan pendiente, entrada a la vuelta 2, final, o el propio motor
saturado ~830 mm/s). Un cambio solo cuenta si baja o sube el tope justo donde este perfil es el mínimo activo.
