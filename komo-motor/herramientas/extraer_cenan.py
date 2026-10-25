"""Extrae las filas de las Tablas peruanas de composición de alimentos (CENAN/INS, 2017)
desde el texto del PDF (pdftotext -layout). Une las dos mitades de cada tabla por código.

Uso: python3 herramientas/extraer_cenan.py tablas.txt salida.json
"""
import json, re, sys

VAL = r"(•|-?\d+(?:,\d+)?)"
P1 = re.compile(r"^\s*([A-Z]{1,2})\s+(\d+)\s+(.+?)\s+" + r"\s+".join([VAL] * 8) + r"\s*$")
P2 = re.compile(r"^\s*" + r"\s+".join([VAL] * 14) + r"\s+([A-Z]{1,2})\s+(\d+)\s*$")
C1 = ["energia_kcal", "energia_kj", "agua_g", "proteina_g", "grasa_g", "carbohidratos_totales_g",
      "carbohidratos_disponibles_g", "fibra_g"]
C2 = ["cenizas_g", "calcio_mg", "fosforo_mg", "zinc_mg", "hierro_mg", "beta_caroteno_ug", "vitamina_a_ug",
      "tiamina_mg", "riboflavina_mg", "niacina_mg", "vitamina_c_mg", "folato_ug", "sodio_mg", "potasio_mg"]

def num(v):
    return None if v == "•" else float(v.replace(",", "."))

def main(txt, salida):
    filas = {}
    for linea in open(txt, encoding="utf-8", errors="replace"):
        m = P1.match(linea)
        if m:
            codigo = f"{m.group(1)} {int(m.group(2))}"
            filas.setdefault(codigo, {})
            filas[codigo].update({"codigo": codigo, "nombre": m.group(3).strip()})
            filas[codigo].update({k: num(v) for k, v in zip(C1, m.groups()[3:])})
            continue
        m = P2.match(linea)
        if m:
            codigo = f"{m.group(15)} {int(m.group(16))}"
            filas.setdefault(codigo, {"codigo": codigo})
            filas[codigo].update({k: num(v) for k, v in zip(C2, m.groups()[:14])})
    completas = {k: v for k, v in filas.items() if "nombre" in v and "calcio_mg" in v}
    json.dump(completas, open(salida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(filas)} códigos leídos, {len(completas)} con ambas mitades")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
