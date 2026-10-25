import random

import pytest

from komo import Persona, calcular, recomendar
from komo.motor import cargar_datos, recetas_posibles

FAMILIA = [
    Persona(edad=38, sexo="h", actividad="intensa", peso=64, talla=162),
    Persona(edad=34, sexo="m", actividad="moderada", estado="lactancia"),
    Persona(edad=11, sexo="h", actividad="intensa"),
    Persona(edad=6, sexo="m", actividad="ligera"),
]
DESPENSA = {"arroz": 2, "papa": 6, "lentejas": 1, "huevo": 4, "zanahoria": 2,
            "cebolla": 1, "ajo": 1, "limon": 3, "aceite": 3}
COMIDAS = ["desayuno", "almuerzo", "cena"]


def gramos_usados(resultado):
    """Suma los gramos de cada ingrediente en todas las comidas."""
    alimentos, _ = cargar_datos()
    por_nombre = {v["nombre"]: k for k, v in alimentos["alimentos"].items()}
    total = {}
    for c in resultado["comidas"]:
        for i in c["ingredientes"]:
            k = por_nombre[i["ingrediente"]]
            total[k] = total.get(k, 0) + i["gramos"]
    return total, alimentos["medidas_caseras"]


# --- requerimientos ---------------------------------------------------------

def test_energia_adulto_con_peso_medido_normal():
    r = calcular(Persona(edad=38, sexo="h", actividad="intensa", peso=64, talla=162))
    assert r.origen_peso == "medido"
    assert r.diario["energia_kcal"] == pytest.approx((11.472 * 64 + 873.1) * 2.2)


def test_menor_usa_peso_de_referencia_aunque_tenga_peso():
    r = calcular(Persona(edad=8, sexo="m", actividad="moderada", peso=15, talla=110))
    assert r.origen_peso == "referencia por edad y sexo"
    assert r.peso_usado == 25.0


def test_adulto_con_imc_fuera_de_rango_usa_referencia_por_talla():
    r = calcular(Persona(edad=40, sexo="m", actividad="ligera", peso=80, talla=150))
    assert r.origen_peso.startswith("referencia por talla")
    assert r.peso_usado == pytest.approx(22 * 1.5 ** 2)


def test_actividad_cambia_energia():
    ligera = calcular(Persona(edad=30, sexo="h", actividad="ligera")).diario["energia_kcal"]
    intensa = calcular(Persona(edad=30, sexo="h", actividad="intensa")).diario["energia_kcal"]
    assert intensa / ligera == pytest.approx(2.20 / 1.55)


def test_lactancia_suma_energia_y_proteina():
    base = calcular(Persona(edad=30, sexo="m", actividad="moderada"))
    lact = calcular(Persona(edad=30, sexo="m", actividad="moderada", estado="lactancia"))
    assert lact.diario["energia_kcal"] - base.diario["energia_kcal"] == pytest.approx(505)
    assert lact.diario["proteina_g"] - base.diario["proteina_g"] == pytest.approx(19)


def test_menor_de_un_anio_no_se_calcula():
    with pytest.raises(ValueError):
        calcular(Persona(edad=0, sexo="h", actividad="ligera"))


# --- filtros de recetas -----------------------------------------------------

def test_receta_que_muele_necesita_batan_molino_o_licuadora():
    _, recetas = cargar_datos()
    despensa = {"papa", "queso", "aceite"}
    sin, _ = recetas_posibles(recetas, "cena", despensa, {"lena"})
    con, _ = recetas_posibles(recetas, "cena", despensa, {"lena", "batan"})
    assert "Papa a la huancaína" not in [r["nombre"] for r in sin]
    assert "Papa a la huancaína" in [r["nombre"] for r in con]


def test_sin_ingrediente_no_hay_receta():
    _, recetas = cargar_datos()
    posibles, descartadas = recetas_posibles(recetas, "desayuno", {"papa", "huevo", "aceite"}, {"gas"})
    assert [r["nombre"] for r in posibles] == ["Papa sancochada con huevo revuelto"]
    assert any(d[0] == "Quinua graneada con queso" for d in descartadas)


# --- motor ------------------------------------------------------------------

def test_nunca_usa_mas_de_lo_que_hay_en_la_despensa():
    r = recomendar(FAMILIA, DESPENSA, {"lena", "batan"}, COMIDAS)
    usado, medidas = gramos_usados(r)
    for ing, g in usado.items():
        assert g <= DESPENSA[ing] * medidas[ing]["g"] + 1


@pytest.mark.parametrize("semilla", range(20))
def test_despensas_aleatorias_respetan_limites(semilla):
    rnd = random.Random(semilla)
    despensa = {k: rnd.choice([0, 1, 2, 3, 5]) for k in DESPENSA}
    despensa["aceite"] = max(despensa["aceite"], 1)
    r = recomendar(FAMILIA, despensa, {"gas"}, rnd.sample(COMIDAS, rnd.randint(1, 3)))
    usado, medidas = gramos_usados(r)
    for ing, g in usado.items():
        assert g <= despensa[ing] * medidas[ing]["g"] + 1


def test_escasez_se_reparte_en_proporcion():
    r = recomendar(FAMILIA, DESPENSA, {"lena", "batan"}, COMIDAS)
    energia = [c["porcentaje"]["energia_kcal"] for c in r["cobertura"]]
    assert max(energia) - min(energia) <= 15
    assert r["cobertura_comun"] < 0.95
    assert "alcanza para cerca del" in r["avisos"][0]


def test_todos_reciben_cada_comida():
    r = recomendar(FAMILIA, DESPENSA, {"lena", "batan"}, COMIDAS)
    for c in r["comidas"]:
        for p in c["porciones"]:
            assert p["items"], f"{p['persona']} sin plato en {c['comida']}"


def test_huevos_se_reparten_uno_por_persona_antes_que_dos():
    r = recomendar(FAMILIA, DESPENSA, {"lena", "batan"}, COMIDAS)
    for c in r["comidas"]:
        huevos = [sum(int(t.split()[0]) for t in p["items"] if "huevo" in t) for p in c["porciones"]]
        if any(huevos):
            assert not (0 in huevos and max(huevos) >= 2), huevos


def test_energia_pareja_tras_redondear():
    r = recomendar(FAMILIA, DESPENSA, {"lena", "batan"}, COMIDAS)
    energia = [c["porcentaje"]["energia_kcal"] for c in r["cobertura"]]
    assert max(energia) - min(energia) <= 10


def test_despensa_abundante_cubre_la_energia():
    abundante = {k: v * 10 for k, v in DESPENSA.items()}
    r = recomendar(FAMILIA, abundante, {"gas"}, ["almuerzo"])
    energia = {c["persona"]: c["porcentaje"]["energia_kcal"] for c in r["cobertura"]}
    # quien no está limitado por el tamaño máximo del plato llega a su requerimiento
    assert energia["Mujer, 6 años"] >= 90
    assert all(v <= 125 for v in energia.values())
    # el límite del padre (actividad intensa) se explica como tamaño de plato, no como falta de comida
    if min(energia.values()) < 90:
        assert "porciones máximas" in r["avisos"][0]


def test_equidad_no_limita_a_quien_puede_comer_mas():
    abundante = {k: v * 10 for k, v in DESPENSA.items()}
    r = recomendar(FAMILIA, abundante, {"gas"}, ["almuerzo"])
    energia = [c["porcentaje"]["energia_kcal"] for c in r["cobertura"]]
    assert max(energia) >= 90


def test_consejo_de_limon_solo_si_hay_limon():
    con = recomendar(FAMILIA, DESPENSA, {"gas"}, ["almuerzo"])
    sin = recomendar(FAMILIA, {**DESPENSA, "limon": 0}, {"gas"}, ["almuerzo"])
    assert any("limón" in t for t in con["comidas"][0]["consejos"])
    assert not any("limón" in t.lower() for c in sin["comidas"] for t in c["consejos"])
    # sin limón la ensalada se prepara igual, sin limón
    assert sin["comidas"] and sin["comidas"][0]["receta"] in ("Lentejas con arroz y ensalada", "Arroz con huevo y ensalada")
    assert not any(i["ingrediente"].startswith("Limón") for i in sin["comidas"][0]["ingredientes"])


def test_cena_sin_refrigeradora_avisa_no_guardar_sobras():
    r = recomendar(FAMILIA, DESPENSA, {"gas"}, ["cena"])
    assert any("refrigeradora" in t for t in r["comidas"][0]["consejos"])
    r = recomendar(FAMILIA, DESPENSA, {"gas", "refrigeradora"}, ["cena"])
    assert not any("refrigeradora" in t for t in r["comidas"][0]["consejos"])


def test_sin_cocina_no_hay_platos():
    r = recomendar(FAMILIA, DESPENSA, set(), ["almuerzo"])
    assert r["comidas"] == []
    assert any("No hay recetas posibles" in a for a in r["avisos"])


def test_condimento_escaso_no_bloquea_el_plato():
    poco_aceite = {**DESPENSA, "aceite": 1}
    r = recomendar(FAMILIA, poco_aceite, {"gas"}, ["desayuno"])
    huevos = sum(int(t.split()[0]) for p in r["comidas"][0]["porciones"] for t in p["items"] if "huevo" in t)
    assert huevos == 4
    usado, medidas = gramos_usados(r)
    assert usado.get("aceite", 0) <= 1 * medidas["aceite"]["g"] + 1


def test_catalogo_grande_resuelve_rapido(tmp_path):
    import json, shutil, time
    from komo.motor import DATOS
    for f in DATOS.iterdir():
        shutil.copy(f, tmp_path / f.name)
    datos = json.loads((tmp_path / "recetas.json").read_text(encoding="utf-8"))
    extra = []
    for r in datos["recetas"]:
        for k in range(4):
            extra.append({**r, "id": f"{r['id']}_{k}", "nombre": f"{r['nombre']} {k}"})
    datos["recetas"] += extra   # ~10 recetas por comida
    (tmp_path / "recetas.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    inicio = time.time()
    r = recomendar(FAMILIA, DESPENSA, {"lena", "batan"}, COMIDAS, directorio=tmp_path)
    assert time.time() - inicio < 10
    assert len(r["comidas"]) == 3


# --- catálogo de la zona (borrador) -------------------------------------------

def test_cada_ingrediente_de_receta_existe_con_medida():
    alimentos, recetas = cargar_datos()
    for r in recetas:
        for c in r["componentes"]:
            for ing in c["por_unidad_g"]:
                assert ing in alimentos["alimentos"], (r["id"], ing)
                assert ing in alimentos["medidas_caseras"], (r["id"], ing)


def test_catalogo_tiene_recetas_para_cada_comida():
    _, recetas = cargar_datos()
    for comida in COMIDAS:
        assert sum(r["comida"] == comida for r in recetas) >= 6


CHACRA = {"papa": 12, "habas_frescas": 2, "maiz_mote": 2, "cuy": 1, "queso": 4, "cebolla": 2, "ajo": 1,
          "aceite": 4, "aji_amarillo": 2, "quinua": 0.5, "zanahoria": 1}


def test_despensa_de_chacra_da_plato_a_todos():
    r = recomendar(FAMILIA, CHACRA, {"lena"}, COMIDAS)
    assert len(r["comidas"]) == 3
    for c in r["comidas"]:
        for p in c["porciones"]:
            assert p["items"], f"{p['persona']} sin plato en {c['comida']}"


def test_sin_cocina_hay_desayuno_frio_y_aviso_con_articulo():
    r = recomendar(FAMILIA, {"pan": 8, "palta": 2}, set(), COMIDAS)
    assert [c["receta"] for c in r["comidas"]] == ["Pan con palta"]
    assert any("para la cena" in a for a in r["avisos"])


def test_sangrecita_sube_el_hierro():
    base = {"papa": 8, "cebolla": 1, "aceite": 3, "ajo": 1, "zanahoria": 2}
    sin = recomendar(FAMILIA, base, {"lena"}, ["cena"])
    con = recomendar(FAMILIA, {**base, "sangrecita": 6}, {"lena"}, ["cena"])
    assert con["comidas"][0]["receta"] == "Sangrecita con papa"
    hierro = lambda r: min(c["porcentaje"]["hierro_mg"] for c in r["cobertura"])
    assert hierro(con) > hierro(sin)


def test_nadie_queda_sin_una_parte_del_plato_en_el_ejemplo():
    r = recomendar(FAMILIA, DESPENSA, {"lena", "batan"}, COMIDAS)
    for c in r["comidas"]:
        partes = [len(p["items"]) for p in c["porciones"]]
        assert min(partes) == max(partes), (c["receta"], [p["items"] for p in c["porciones"]])
