"""Genera komo/datos/alimentos.json a partir de las Tablas peruanas (CENAN/INS, 2017).

Para agregar un ingrediente: añade su id, su código CENAN y su medida casera en MAPA.
Uso: python3 herramientas/generar_alimentos.py
"""
import json
from pathlib import Path

DATOS = Path(__file__).resolve().parent.parent / "komo" / "datos"
CAMPOS = ["energia_kcal", "proteina_g", "grasa_g", "carbohidratos_disponibles_g", "carbohidratos_totales_g",
          "fibra_g", "calcio_mg", "zinc_mg", "hierro_mg", "vitamina_a_ug", "vitamina_c_mg", "folato_ug", "sodio_mg"]

# id: (código Tablas peruanas 2017, medida casera, plural, gramos netos por medida, código Tablas auxiliares 2016)
# Los gramos por medida vienen del Módulo I de las Tablas auxiliares CENAN/INS (2016), peso neto.
MAPA = {
    "arroz":     ("A 3",  "taza", "tazas", 281.8, "1-4 taza de loza al ras"),
    "papa":      ("U 18", "unidad mediana", "unidades medianas", 162.5, "12-45 papa amarilla, unidad mediana"),
    "lentejas":  ("T 54", "taza", "tazas", 259.8, "11-116 lenteja grande, taza de loza al ras"),
    "huevo":     ("J 4",  "unidad", "unidades", 59.9, "8-3 huevo de gallina, unidad mediana"),
    "zanahoria": ("B 85", "unidad", "unidades", 157.8, "2-82 zanahoria amarilla, unidad mediana"),
    "cebolla":   ("B 29", "unidad", "unidades", 194.9, "2-38 cebolla de cabeza roja, unidad mediana"),
    "ajo":       ("B 13", "cabeza", "cabezas", 49.8, "2-17 ajos, cabeza mediana"),
    "limon":     ("C 34", "unidad", "unidades", 15.6, "3-51 limón, unidad mediana"),
    "aceite":    ("D 9",  "cucharada", "cucharadas", 6.6, "4-5 aceite vegetal de soya, cucharada llena"),
    "quinua":    ("A 54", "taza", "tazas", 243.0, "1-144 quinua blanca cruda, taza de loza al ras"),
    "queso":     ("G 14", "tajada", "tajadas", 19.4, "7-22 queso fresco de vaca, tajada mediana delgada"),
    # --- ingredientes de la zona (Churubamba, Huánuco). Propuesta para validar con Jazmín ---
    # Tubérculos y raíces
    "papa_blanca":  ("U 19", "unidad mediana", "unidades medianas", 197.7, "12-52 papa blanca perricholi, unidad mediana"),
    "olluco":       ("U 17", "unidad mediana", "unidades medianas", 44.7, "12-39 olluco entero, unidad mediana (8 cm)"),
    "oca":          ("U 50", "unidad mediana", "unidades medianas", 39.1, "12-36 oca, unidad mediana (10 cm)"),
    "camote":       ("U 3",  "unidad mediana", "unidades medianas", 276.7, "12-9 camote amarillo, unidad mediana"),
    "yuca":         ("U 36", "trozo mediano", "trozos medianos", 158.5, "12-85 yuca blanca, trozo mediano (6 x 7 cm)"),
    "papa_seca":    ("U 25", "taza", "tazas", 186.5, "12-67 papa seca, taza de acero llena"),
    # Cereales
    "maiz_mote":    ("A 41", "taza", "tazas", 120.0, "1-115 maíz para mote pelado, taza de acero al ras"),
    "choclo":       ("A 34", "taza", "tazas", 209.8, "1-98 maíz fresco en granos, taza de loza al ras"),
    "trigo":        ("A 68", "taza", "tazas", 218.9, "1-181 trigo pelado, taza de acero al ras"),
    "avena":        ("A 7",  "taza", "tazas", 84.6, "1-38 avena en hojuela cruda, taza de acero al ras"),
    "pan":          ("A 49", "unidad", "unidades", 32.0, "pan francés de panadería, unidad mediana (Módulo I, p. 21)"),
    # Menestras
    "habas_secas":  ("T 49", "taza", "tazas", 213.4, "haba seca partida, taza de loza al ras (Módulo I, p. 67)"),
    "arveja_seca":  ("T 3",  "taza", "tazas", 305.4, "11-8 arveja seca partida, taza de loza al ras"),
    "frejol":       ("T 6",  "taza", "tazas", 298.8, "11-31 frijol canario, taza de loza al ras"),
    "habas_frescas":("T 47", "taza", "tazas", 179.8, "11-92 haba fresca sin cáscara, taza de loza al ras"),
    "arveja_fresca":("T 2",  "taza", "tazas", 205.1, "11-2 arveja fresca, taza de loza al ras"),
    # Alimentos de origen animal
    "cuy":          ("F 74", "cuy mediano", "cuyes medianos", 304.5, "6-39 cuy entero, unidad mediana, peso neto"),
    "pollo":        ("F 26", "pierna mediana", "piernas medianas", 85.8, "6-106 pollo, pierna mediana, peso neto"),
    "higado_pollo": ("F 28", "hígado mediano", "hígados medianos", 51.5, "6-99 pollo, hígado de, unidad mediana"),
    "res":          ("F 35", "trozo mediano", "trozos medianos", 123.3, "6-132 res, carne pulpa, trozo mediano"),
    "higado_res":   ("F 38", "trozo pequeño", "trozos pequeños", 58.7, "6-124 res, hígado de, unidad pequeña"),
    "sangrecita":   ("F 29", "cucharada", "cucharadas", 15.0, "PROVISIONAL: sin dato en las Tablas auxiliares 2016; validar con Jazmín"),
    "atun":         ("E 21", "cucharada", "cucharadas", 13.3, "5-9 atún en trozos en conserva, cucharada llena"),
    "trucha":       ("E 83", "unidad pequeña", "unidades pequeñas", 146.2, "5-81 trucha pequeña sin cabeza, cola ni espinazo"),
    "leche_evaporada": ("G 7", "taza", "tazas", 370.7, "7-1 leche evaporada entera, taza de loza al ras"),
    "leche_fresca": ("G 11", "taza", "tazas", 359.8, "7-7 leche fresca de vaca, taza de loza al ras"),
    # Verduras y frutas
    "zapallo":      ("B 124","trozo mediano", "trozos medianos", 234.1, "2-93 zapallo macre, trozo mediano"),
    "col":          ("B 31", "cuarto de col", "cuartos de col", 150.0, "col, 1/4 de cabeza pequeña (Módulo I, p. 26)"),
    "tomate":       ("B 79", "unidad mediana", "unidades medianas", 129.6, "tomate italiano, unidad mediana (Módulo I, p. 27)"),
    "aji_amarillo": ("B 3",  "unidad mediana", "unidades medianas", 46.3, "ají amarillo, unidad mediana (Módulo I, p. 25)"),
    "naranja":      ("C 48", "unidad mediana", "unidades medianas", 222.5, "3-110 naranja de mesa, unidad mediana, pulpa"),
    "platano":      ("C 73", "unidad mediana", "unidades medianas", 53.4, "3-159 plátano manzano, unidad mediana"),
    "palta":        ("C 55", "unidad mediana", "unidades medianas", 201.4, "3-122 palta fuerte, unidad mediana"),
    "azucar":       ("K 1",  "cucharadita", "cucharaditas", 6.5, "9-11 azúcar, cucharadita llena"),
}

def main():
    tabla = json.loads((DATOS / "tablas_cenan_2017.json").read_text(encoding="utf-8"))
    alimentos, medidas = {}, {}
    for ident, (codigo, unidad, plural, g, fuente_medida) in MAPA.items():
        fila = tabla[codigo]
        alimentos[ident] = {"nombre": fila["nombre"], "codigo_cenan": codigo, "verificado": True,
                            **{k: fila.get(k) for k in CAMPOS}}
        medidas[ident] = {"unidad": unidad, "plural": plural, "g": g, "fuente": "Tablas auxiliares CENAN/INS 2016, " + fuente_medida}
    salida = {
        "_nota": "Valores por 100 g de porción comestible, tomados de las Tablas peruanas de composición de "
                 "alimentos (CENAN/INS, 2017). null = dato no reportado en la tabla (se trata como 0). "
                 "Generado con herramientas/generar_alimentos.py; no editar a mano.",
        "alimentos": alimentos,
        "medidas_caseras": medidas,
    }
    (DATOS / "alimentos.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(alimentos)} alimentos generados")

if __name__ == "__main__":
    main()
