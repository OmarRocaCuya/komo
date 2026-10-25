"""Ejemplo: la familia del diseño de Komo (sierra, fogón y batán, sin refrigeradora).

Uso:  python3 ejemplo.py
"""

from komo import Persona, recomendar
from komo.motor import ETIQUETAS

familia = [
    Persona(edad=38, sexo="h", actividad="intensa", peso=64, talla=162),
    Persona(edad=34, sexo="m", actividad="moderada", estado="lactancia"),
    Persona(edad=11, sexo="h", actividad="intensa"),
    Persona(edad=6, sexo="m", actividad="ligera"),
]

despensa = {  # cantidades en medidas caseras (ver medidas_caseras en datos/alimentos.json)
    "arroz": 2, "papa": 6, "lentejas": 1, "huevo": 4, "zanahoria": 2,
    "cebolla": 1, "ajo": 1, "limon": 3, "aceite": 3,
}
utensilios = {"lena", "batan"}
comidas = ["desayuno", "almuerzo", "cena"]


def imprimir(r):
    for c in r["comidas"]:
        print(f"\n=== {c['comida'].upper()}: {c['receta']} ===")
        for p in c["porciones"]:
            print(f"  {p['persona']}: " + ", ".join(p["items"]))
        print("  Para cocinar todo:")
        for i in c["ingredientes"]:
            print(f"    - {i['ingrediente']}: {i['cantidad']} ({i['gramos']} g)")
        for t in c["consejos"]:
            print(f"  Consejo: {t}")
    print("\n=== COBERTURA DEL DÍA (comidas elegidas, % del requerimiento) ===")
    for p in r["cobertura"]:
        pct = p["porcentaje"]
        print(f"  {p['persona']} ({p['requerimiento_dia_kcal']} kcal/día, peso {p['peso_usado_kg']} kg, {p['origen_peso']}):")
        print("    " + " · ".join(f"{ETIQUETAS[k]} {v}%" for k, v in pct.items()))
    print("\n=== SOBRA EN LA DESPENSA ===")
    for k, v in r["despensa_restante"].items():
        print(f"  {k}: {v}")
    if not r["despensa_restante"]:
        print("  Nada")
    print("\n=== RECETAS DESCARTADAS ===")
    for comida, lista in r["descartes"].items():
        for nombre, ing, ut in lista:
            motivo = []
            if ing:
                motivo.append("faltan " + ", ".join(ing))
            if ut:
                motivo.append("falta " + " o ".join(ut[0]))
            print(f"  {comida}: {nombre} ({'; '.join(motivo)})")
    print("\n=== AVISOS ===")
    for a in r["avisos"]:
        print(f"  - {a}")


if __name__ == "__main__":
    imprimir(recomendar(familia, despensa, utensilios, comidas))
