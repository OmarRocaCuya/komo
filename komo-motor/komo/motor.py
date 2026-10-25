"""Motor de sustitución de Komo (prototipo).

Flujo:
1. Calcula el requerimiento diario de cada persona (requerimientos.py).
2. Filtra recetas por comida, utensilios disponibles e ingredientes en la despensa.
3. Para cada combinación de recetas (una por comida elegida) resuelve dos modelos
   de programación lineal sobre la MISMA despensa:
   a. Equidad: maximiza la fracción t de energía que TODOS reciben por igual
      (si la despensa no alcanza, la escasez se reparte en proporción).
   b. Calidad: con esa equidad fija, ajusta el reparto entre comidas, la
      proteína, los micronutrientes y la grasa.
4. Elige la combinación con mayor t (y luego mejor calidad) y redondea a medidas
   caseras sin pasarse de lo que hay en la despensa.

Cada persona recibe el plato completo: sus componentes mantienen la proporción de
la receta, con un margen de ±50 % para ajustar nutrientes.
"""

import itertools
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from . import reglas
from .requerimientos import NUTRIENTES, REPARTO_COMIDAS, calcular

DATOS = Path(__file__).parent / "datos"
MICROS = ["hierro_mg", "zinc_mg", "calcio_mg", "vitamina_a_ug", "vitamina_c_mg"]
ETIQUETAS = {"energia_kcal": "energía", "proteina_g": "proteína", "hierro_mg": "hierro", "zinc_mg": "zinc",
             "calcio_mg": "calcio", "vitamina_a_ug": "vit. A", "vitamina_c_mg": "vit. C"}

MARGEN_PROPORCION = 0.35  # cada componente puede ir de 65 % a 135 % de la proporción de la receta
GRASA_MAX = 0.35          # fracción máxima de la energía que viene de grasa
TOLERANCIA_EQUIDAD = 0.01
ARTICULO = {"desayuno": "el", "almuerzo": "el", "cena": "la"}
FLEXIBLES = {"aceite", "ajo", "limon", "azucar", "aji_amarillo"}  # condimentos: se usa lo que alcance, no limitan el plato
MAX_RECETAS_POR_COMIDA = 3
CANDIDATOS_REDONDEO = 6   # combinaciones que se comparan ya redondeadas
TOLERANCIA_HUECOS = 0.03  # se acepta hasta 3 puntos menos de cobertura para que nadie quede sin una parte del plato
PISO_COMIDA = 0.6         # cada comida cubre al menos 60 % de su parte (si la despensa lo permite)

# Pesos del modelo de calidad. Más alto = más importante.
PESO_ENERGIA_FALTA = 10.0
PESO_ENERGIA_EXCESO = 3.0
PESO_PROTEINA = 6.0
PESO_EQUIDAD_PROTEINA = 20.0
PESO_BALANCE = 4.0
PESO_MICRO = 1.0
PESO_GRASA = 2.0


def cargar_datos(directorio=DATOS):
    alimentos = json.loads((Path(directorio) / "alimentos.json").read_text(encoding="utf-8"))
    recetas = json.loads((Path(directorio) / "recetas.json").read_text(encoding="utf-8"))
    return alimentos, recetas["recetas"]


def _nutrientes_por_unidad(componente, alimentos):
    total = {n: 0.0 for n in NUTRIENTES + ["grasa_g"]}
    for ing, gramos in componente["por_unidad_g"].items():
        fila = alimentos[ing]
        for n in total:
            total[n] += (fila.get(n) or 0) * gramos / 100.0
    return total


def _adaptar(receta, despensa_ids):
    """Quita de la receta los ingredientes opcionales que no hay en la despensa."""
    r = dict(receta)
    r["componentes"] = []
    for c in receta["componentes"]:
        c = dict(c)
        opcionales = set(c.get("opcionales", []))
        c["por_unidad_g"] = {ing: g for ing, g in c["por_unidad_g"].items()
                             if ing not in opcionales or ing in despensa_ids}
        r["componentes"].append(c)
    return r


def recetas_posibles(recetas, comida, despensa_ids, utensilios):
    posibles, descartadas = [], []
    for r in recetas:
        if r["comida"] != comida:
            continue
        r = _adaptar(r, despensa_ids)
        faltan_utensilios = [g for g in r["requiere"] if not set(g) & utensilios]
        ingredientes = {ing for c in r["componentes"] for ing in c["por_unidad_g"]}
        faltan_ingredientes = sorted(ingredientes - despensa_ids)
        if faltan_utensilios or faltan_ingredientes:
            descartadas.append((r["nombre"], faltan_ingredientes, faltan_utensilios))
        else:
            posibles.append(r)
    return posibles, descartadas


class _Modelo:
    def __init__(self):
        self.lb, self.ub, self.c = [], [], []
        self.A_ub, self.b_ub = [], []

    def var(self, lb=0.0, ub=None, costo=0.0):
        self.lb.append(lb)
        self.ub.append(ub)
        self.c.append(costo)
        return len(self.c) - 1

    def menor_igual(self, coefs, valor):
        self.A_ub.append(coefs)
        self.b_ub.append(valor)

    def resolver(self):
        n = len(self.c)
        A = np.zeros((len(self.A_ub), n))
        for i, fila in enumerate(self.A_ub):
            for j, v in fila.items():
                A[i, j] += v
        return linprog(c=np.array(self.c), A_ub=A, b_ub=self.b_ub,
                       bounds=list(zip(self.lb, self.ub)), method="highs")


def _construir(reqs, combinacion, despensa_g, nut_comp, t_minimo=None, piso_comida=0.0):
    """Si t_minimo es None, construye el modelo de equidad (maximizar t).
    Si no, construye el modelo de calidad con cobertura mínima t_minimo."""
    mod = _Modelo()
    equidad = t_minimo is None
    fraccion_dia = sum(REPARTO_COMIDAS[c] for c, _ in combinacion)
    t = mod.var(0, 1, -1.0) if equidad else None
    # en el modelo de calidad, penaliza que a una persona le falte mucha más proteína que a otra
    peor_proteina = None if equidad else mod.var(0, 1, PESO_EQUIDAD_PROTEINA)
    x = {}
    for i, req in enumerate(reqs):
        dia = req.diario
        energia_dia = {}
        for comida, receta in combinacion:
            s = mod.var(0, None)  # tamaño del plato de la persona i en esta comida
            for comp in receta["componentes"]:
                idx = mod.var(0, comp["max"])
                x[(i, comida, comp["id"])] = idx
                r = comp["base"]
                piso = comp.get("proporcion_min", 1 - MARGEN_PROPORCION)
                mod.menor_igual({idx: -1.0, s: piso * r}, 0.0)
                mod.menor_igual({idx: 1.0, s: -(1 + MARGEN_PROPORCION) * r}, 0.0)
                energia_dia[idx] = nut_comp[(comida, comp["id"])]["energia_kcal"]
            if not equidad:
                # la meta es el requerimiento completo: la equidad solo fija un mínimo común (t_minimo)
                meta = dia["energia_kcal"] * REPARTO_COMIDAS[comida]
                if piso_comida:
                    # nadie se queda sin plato: cada comida cubre al menos una fracción de su parte
                    mod.menor_igual({x[(i, comida, c["id"])]: -nut_comp[(comida, c["id"])]["energia_kcal"]
                                     for c in receta["componentes"]}, -piso_comida * t_minimo * meta)
                falta = mod.var(0, 1, PESO_ENERGIA_FALTA)
                exceso = mod.var(0, None, PESO_ENERGIA_EXCESO)
                filas = {x[(i, comida, c["id"])]: nut_comp[(comida, c["id"])]["energia_kcal"] / meta
                         for c in receta["componentes"]}
                # energía/meta + falta - exceso = 1  (como dos desigualdades)
                mod.menor_igual({**filas, falta: 1.0, exceso: -1.0}, 1.0)
                mod.menor_igual({**{k: -v for k, v in filas.items()}, falta: -1.0, exceso: 1.0}, -1.0)
                # balance: cada comida de la persona se acerca a su parte de la cobertura común
                if t_minimo > 0.01:
                    escala = 1.0 / max(t_minimo, 0.05)
                    bajo = mod.var(0, None, PESO_BALANCE)
                    alto = mod.var(0, None, PESO_BALANCE / 4)
                    filas_b = {k: v * escala for k, v in filas.items()}
                    mod.menor_igual({**filas_b, bajo: 1.0, alto: -1.0}, 1.0)
                    mod.menor_igual({**{k: -v for k, v in filas_b.items()}, bajo: -1.0, alto: 1.0}, -1.0)
                grasa = mod.var(0, None, PESO_GRASA / meta)
                fila = {x[(i, comida, c["id"])]: 9 * nut_comp[(comida, c["id"])]["grasa_g"]
                        - GRASA_MAX * nut_comp[(comida, c["id"])]["energia_kcal"] for c in receta["componentes"]}
                fila[grasa] = -1.0
                mod.menor_igual(fila, 0.0)
        meta_dia = dia["energia_kcal"] * fraccion_dia
        if equidad:
            # energía_dia >= t * meta_dia
            mod.menor_igual({**{k: -v for k, v in energia_dia.items()}, t: meta_dia}, 0.0)
        else:
            mod.menor_igual({k: -v for k, v in energia_dia.items()}, -(t_minimo - TOLERANCIA_EQUIDAD) * meta_dia)
            for nutriente, peso in [("proteina_g", PESO_PROTEINA)] + [(m, PESO_MICRO) for m in MICROS]:
                meta = dia[nutriente] * fraccion_dia
                falta = mod.var(0, 1, peso)
                fila = {falta: -meta}
                for comida, receta in combinacion:
                    for c in receta["componentes"]:
                        fila[x[(i, comida, c["id"])]] = -nut_comp[(comida, c["id"])][nutriente]
                mod.menor_igual(fila, -meta)
                if nutriente == "proteina_g":
                    mod.menor_igual({falta: 1.0, peor_proteina: -1.0}, 0.0)
    # despensa compartida por todas las comidas
    recetas = dict(combinacion)
    for ing, disponible in despensa_g.items():
        fila = {}
        for (i, comida, comp_id), idx in x.items():
            comp = next(c for c in recetas[comida]["componentes"] if c["id"] == comp_id)
            g = comp["por_unidad_g"].get(ing, 0)
            if g:
                fila[idx] = g
        if fila:
            mod.menor_igual(fila, disponible)
    return mod, x, t


def _optimizar(reqs, combinacion, despensa_g, alimentos):
    nut_comp = {}
    for comida, receta in combinacion:
        for comp in receta["componentes"]:
            nut_comp[(comida, comp["id"])] = _nutrientes_por_unidad(comp, alimentos)
    mod, _, t = _construir(reqs, combinacion, despensa_g, nut_comp)
    res = mod.resolver()
    if res.status != 0:
        return None
    t_max = float(res.x[t])
    # techo sin límite de despensa: separa "falta comida" de "el plato no alcanza"
    mod_sin, _, t_sin = _construir(reqs, combinacion, {}, nut_comp)
    res_sin = mod_sin.resolver()
    t_techo = float(res_sin.x[t_sin]) if res_sin.status == 0 else 1.0
    for piso in (PISO_COMIDA, 0.3, 0.0):
        mod, x, _ = _construir(reqs, combinacion, despensa_g, nut_comp, t_minimo=t_max, piso_comida=piso)
        res = mod.resolver()
        if res.status == 0:
            break
    else:
        return None
    valores = {k: float(res.x[idx]) for k, idx in x.items()}
    return {"t": t_max, "t_techo": t_techo, "objetivo": float(res.fun), "x": valores, "nut_comp": nut_comp,
            "fraccion_dia": sum(REPARTO_COMIDAS[c] for c, _ in combinacion)}


def _redondear(x, combinacion, despensa_g, energia_comp=None, meta_persona=None):
    """Redondea a medidas caseras respetando la despensa. Si se dan energia_comp
    {(comida, comp_id): kcal por medida} y meta_persona {i: kcal}, los ajustes favorecen
    a la persona con menor cobertura (misma regla de equidad que el modelo)."""
    recetas = dict(combinacion)

    def cobertura(i):
        if not energia_comp:
            return 0.0
        kcal = sum(q * energia_comp[(c, comp)] for (j, c, comp), q in valores.items() if j == i)
        return kcal / meta_persona[i]
    comp_de, valores = {}, {}
    for clave, crudo in x.items():
        _, comida, comp_id = clave
        comp = next(c for c in recetas[comida]["componentes"] if c["id"] == comp_id)
        comp_de[clave] = comp
        q = round(crudo / comp["paso"]) * comp["paso"]
        if q == 0 and crudo >= 0.3 * comp["paso"]:
            q = comp["paso"]  # una porción pequeña se sirve como la medida mínima, no desaparece
        valores[clave] = q

    def uso():
        total = {}
        for clave, q in valores.items():
            for ing, g in comp_de[clave]["por_unidad_g"].items():
                total[ing] = total.get(ing, 0) + q * g
        return total

    while True:
        exceso = [ing for ing, g in uso().items() if ing in despensa_g and g > despensa_g[ing] + 1e-6]
        if not exceso:
            break
        ing = exceso[0]
        candidatos = [k for k in valores if valores[k] > 0 and ing in comp_de[k]["por_unidad_g"]]
        # quitar a quien tiene más cobertura; a igualdad, donde el redondeo subió más
        k = max(candidatos, key=lambda k: (round(cobertura(k[0]), 3), valores[k] - x[k]))
        valores[k] = max(0.0, valores[k] - comp_de[k]["paso"])

    # lo que sobró se entrega a la persona con menor cobertura, sin alejarse del plan del modelo
    while True:
        total = uso()
        candidatos = []
        for k, q in valores.items():
            comp = comp_de[k]
            if q + comp["paso"] > comp["max"] or q + comp["paso"] > x[k] + 0.75 * comp["paso"]:
                continue
            cabe = all(total.get(ing, 0) + comp["paso"] * g <= despensa_g[ing] + 1e-6
                       for ing, g in comp["por_unidad_g"].items() if ing in despensa_g)
            if cabe:
                candidatos.append((round(cobertura(k[0]), 3), -(x[k] - q), k))
        if not candidatos:
            break
        _, _, k = min(candidatos)
        valores[k] += comp_de[k]["paso"]

    # nadie se queda sin un componente mientras otro recibe dos medidas o más
    # (con huevos: todos reciben uno antes de que alguien reciba dos)
    grupos = {}
    for k in valores:
        grupos.setdefault((k[1], k[2]), []).append(k)
    for claves in grupos.values():
        while True:
            sin = [k for k in claves if valores[k] == 0]
            con_mas = [k for k in claves if valores[k] >= 2 * comp_de[k]["paso"]]
            if not sin or not con_mas:
                break
            dador = max(con_mas, key=lambda k: valores[k])
            receptor = min(sin, key=lambda k: cobertura(k[0]))
            paso = comp_de[dador]["paso"]
            valores[dador] -= paso
            valores[receptor] += paso
    return valores, uso()


FRACCIONES = {0.0: "", 0.25: "¼", 0.5: "½", 0.75: "¾"}


def medida(q, singular, plural):
    q = round(q * 4) / 4
    entero = int(q)
    frac = FRACCIONES[q - entero]
    if entero == 0:
        texto = frac or "0"
    else:
        texto = f"{entero} {frac}".strip()
    return f"{texto} {singular if q <= 1 else plural}"


def _texto_porcion(q, comp):
    m = medida(q, comp["unidad"], comp["plural"])
    return f"{m} de {comp['nombre']}" if comp["nombre"] else m


def recomendar(personas, despensa, utensilios, comidas, directorio=DATOS):
    """personas: lista de Persona; despensa: {id_alimento: cantidad en medidas caseras};
    utensilios: conjunto de ids; comidas: lista entre 'desayuno', 'almuerzo', 'cena'."""
    alimentos_json, recetas = cargar_datos(directorio)
    alimentos = alimentos_json["alimentos"]
    medidas = alimentos_json["medidas_caseras"]
    avisos = []

    reqs = []
    for p in personas:
        try:
            r = calcular(p)
            reqs.append(r)
            avisos.extend(f"{p.descripcion()}: {a}" for a in r.avisos)
        except ValueError as e:
            avisos.append(f"{p.descripcion()}: {e}")
    if not reqs:
        return {"comidas": [], "cobertura": [], "despensa_restante": {}, "descartes": {},
                "avisos": avisos + ["No hay personas para calcular."]}

    despensa_ids = {k for k, v in despensa.items() if v > 0}
    despensa_g = {k: v * medidas[k]["g"] for k, v in despensa.items() if v > 0}
    # los condimentos flexibles no limitan el plato: se usa lo que alcance
    estricta = {k: g for k, g in despensa_g.items() if k not in FLEXIBLES}
    utensilios = set(utensilios)

    opciones, descartes = [], {}
    for comida in comidas:
        posibles, descartadas = recetas_posibles(recetas, comida, despensa_ids, utensilios)
        descartes[comida] = descartadas
        if not posibles:
            avisos.append(f"No hay recetas posibles para {ARTICULO[comida]} {comida} con esta despensa y estos utensilios.")
            continue
        opciones.append([(comida, r) for r in posibles])
    if not opciones:
        return {"comidas": [], "cobertura": [], "despensa_restante": {}, "descartes": descartes, "avisos": avisos}

    escala = {}
    for _ in range(2):  # 2.a vuelta solo si faltan condimentos: se reajusta con lo que alcanza
        ajustadas = [[(c, _escalar(r, escala)) for c, r in grupo] for grupo in opciones]
        resultado = _mejor_combinacion(reqs, ajustadas, estricta, alimentos)
        if resultado is None:
            return {"comidas": [], "cobertura": [], "despensa_restante": {}, "descartes": descartes,
                    "avisos": avisos + ["El modelo no encontró solución."]}
        sol, combinacion = resultado
        energia_comp = {k: v["energia_kcal"] for k, v in sol["nut_comp"].items()}
        meta_persona = {i: r.diario["energia_kcal"] * sol["fraccion_dia"] for i, r in enumerate(reqs)}
        valores, usado = _redondear(sol["x"], combinacion, estricta, energia_comp, meta_persona)
        uso_flex = _uso(valores, combinacion, FLEXIBLES)
        nueva = {ing: min(1.0, despensa_g.get(ing, 0) / g) for ing, g in uso_flex.items() if g > 0}
        if all(f >= 0.999 for f in nueva.values()):
            break
        escala = {ing: escala.get(ing, 1.0) * f for ing, f in nueva.items()}
    # tope final de condimentos: nunca más de lo que hay
    tope = {ing: min(1.0, despensa_g.get(ing, 0) / g) for ing, g in _uso(valores, combinacion, FLEXIBLES).items() if g > 0}
    recetas_uso = {c: _escalar(r, tope) for c, r in combinacion}
    usado = _uso(valores, list(recetas_uso.items()), None)

    salida_comidas = []
    for comida, receta in recetas_uso.items():
        porciones, total_ing = [], {}
        for i, req in enumerate(reqs):
            items = []
            for comp in receta["componentes"]:
                q = valores[(i, comida, comp["id"])]
                for ing, g in comp["por_unidad_g"].items():
                    total_ing[ing] = total_ing.get(ing, 0) + q * g
                if q > 0:
                    items.append(_texto_porcion(q, comp))
            porciones.append({"persona": req.persona.descripcion(), "items": items})
        ingredientes = []
        for ing, g in total_ing.items():
            if g <= 0.5:
                continue
            m = medidas[ing]
            q = max(0.25, round(g / m["g"] * 4) / 4)
            ingredientes.append({"ingrediente": alimentos[ing]["nombre"],
                                 "cantidad": medida(q, m["unidad"], m["plural"]), "gramos": round(g)})
        salida_comidas.append({
            "comida": comida, "receta": receta["nombre"], "porciones": porciones,
            "ingredientes": ingredientes,
            "consejos": reglas.consejos_receta(receta, comida, despensa_ids, utensilios),
            "pasos": receta["pasos"],
        })

    cobertura = []
    for i, req in enumerate(reqs):
        consumo = {n: 0.0 for n in NUTRIENTES}
        for comida, receta in recetas_uso.items():
            for comp in receta["componentes"]:
                q = valores[(i, comida, comp["id"])]
                n = _nutrientes_por_unidad(comp, alimentos)
                for k in consumo:
                    consumo[k] += q * n[k]
        meta = {k: req.diario[k] * sol["fraccion_dia"] for k in NUTRIENTES}
        cobertura.append({
            "persona": req.persona.descripcion(),
            "peso_usado_kg": round(req.peso_usado, 1),
            "origen_peso": req.origen_peso,
            "requerimiento_dia_kcal": round(req.diario["energia_kcal"]),
            "porcentaje": {k: round(100 * consumo[k] / meta[k]) for k in NUTRIENTES},
        })

    if sol["t"] < sol["t_techo"] - 0.02:
        avisos.insert(0, f"La despensa alcanza para cerca del {round(100 * sol['t'])} % de la energía que necesitan "
                         f"en las comidas elegidas. Komo repartió lo disponible en la misma proporción para todos.")
    elif sol["t"] < 0.95:
        avisos.insert(0, f"Las porciones máximas de estos platos cubren cerca del {round(100 * sol['t'])} % de la "
                         f"energía de las personas más activas. Conviene sumar un refrigerio o fiambre.")
    bajos = sorted({ETIQUETAS[k] for c in cobertura for k, v in c["porcentaje"].items()
                    if k in MICROS and v < 50})
    if bajos:
        avisos.append("Con esta despensa queda bajo: " + ", ".join(bajos) + ".")

    restante = {}
    for ing, g in despensa_g.items():
        sobra = g - usado.get(ing, 0)
        m = medidas[ing]
        q = round(sobra / m["g"] * 4) / 4
        if q > 0:
            restante[alimentos[ing]["nombre"]] = medida(q, m["unidad"], m["plural"])

    return {
        "cobertura_comun": round(sol["t"], 3),
        "comidas": salida_comidas,
        "cobertura": cobertura,
        "despensa_restante": restante,
        "avisos": avisos + reglas.avisos_dia(),
        "descartes": descartes,
    }


def _escalar(receta, escala):
    """Copia de la receta con los condimentos flexibles reducidos según 'escala'."""
    if not escala:
        return receta
    r = dict(receta)
    r["componentes"] = [{**c, "por_unidad_g": {ing: g * escala.get(ing, 1.0) for ing, g in c["por_unidad_g"].items()}}
                        for c in receta["componentes"]]
    return r


def _uso(valores, combinacion, solo):
    recetas = dict(combinacion)
    total = {}
    for (i, comida, comp_id), q in valores.items():
        comp = next(c for c in recetas[comida]["componentes"] if c["id"] == comp_id)
        for ing, g in comp["por_unidad_g"].items():
            if solo is None or ing in solo:
                total[ing] = total.get(ing, 0) + q * g
    return total


def _mejor_combinacion(reqs, opciones, despensa_g, alimentos):
    """Preselecciona hasta MAX_RECETAS_POR_COMIDA recetas por comida y prueba sus combinaciones."""
    filtradas = []
    for grupo in opciones:
        if len(grupo) > MAX_RECETAS_POR_COMIDA:
            puntajes = []
            for item in grupo:
                sol = _optimizar(reqs, [item], despensa_g, alimentos)
                if sol is not None:
                    puntajes.append(((-round(sol["t"], 3), sol["objetivo"]), item))
            puntajes.sort(key=lambda p: p[0])
            grupo = [item for _, item in puntajes[:MAX_RECETAS_POR_COMIDA]] or grupo[:MAX_RECETAS_POR_COMIDA]
        filtradas.append(grupo)
    candidatos = []
    for combinacion in itertools.product(*filtradas):
        sol = _optimizar(reqs, list(combinacion), despensa_g, alimentos)
        if sol is not None:
            candidatos.append(((-round(sol["t"], 3), sol["objetivo"]), sol, list(combinacion)))
    if not candidatos:
        return None
    candidatos.sort(key=lambda c: c[0])
    # entre las combinaciones casi tan buenas como la mejor, se prefiere la que, ya redondeada,
    # no deja a nadie sin una parte del plato que otros sí reciben (por ejemplo, sin huevo)
    t_mejor = -candidatos[0][0][0]
    finalistas = [c for c in candidatos[:CANDIDATOS_REDONDEO] if -c[0][0] >= t_mejor - TOLERANCIA_HUECOS]
    _, sol, comb = min(finalistas, key=lambda c: (_huecos(c[1], c[2], despensa_g, reqs), c[0]))
    return sol, comb


def _huecos(sol, combinacion, despensa_g, reqs):
    """Cuenta las partes de un plato que alguien no recibe mientras otros sí, tras redondear."""
    energia_comp = {k: v["energia_kcal"] for k, v in sol["nut_comp"].items()}
    meta = {i: r.diario["energia_kcal"] * sol["fraccion_dia"] for i, r in enumerate(reqs)}
    valores, _ = _redondear(sol["x"], combinacion, despensa_g, energia_comp, meta)
    grupos = {}
    for (i, comida, comp), q in valores.items():
        grupos.setdefault((comida, comp), []).append(q)
    return sum(sum(q == 0 for q in qs) for qs in grupos.values() if any(qs))
