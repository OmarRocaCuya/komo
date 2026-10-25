"""Escenarios de despensas típicas de Churubamba para revisar el catálogo de la zona."""
import time
from komo import Persona, recomendar

FAMILIA = [Persona(edad=38, sexo="h", actividad="intensa", peso=64, talla=162),
           Persona(edad=34, sexo="m", actividad="moderada", estado="lactancia"),
           Persona(edad=11, sexo="h", actividad="intensa"),
           Persona(edad=6, sexo="m", actividad="ligera")]
COMIDAS = ["desayuno", "almuerzo", "cena"]
ESCENARIOS = {
    "Chacra en cosecha (papa, habas, mote, cuy)": (
        {"papa": 12, "habas_frescas": 2, "maiz_mote": 2, "cuy": 1, "queso": 4, "cebolla": 2, "ajo": 1,
         "aceite": 4, "aji_amarillo": 2, "quinua": 0.5, "zanahoria": 1}, {"lena"}),
    "Fin de mes (arroz, frejol, papa, sangrecita)": (
        {"arroz": 2, "frejol": 1, "papa": 6, "sangrecita": 6, "cebolla": 1, "ajo": 1, "aceite": 3, "pan": 4,
         "avena": 0.5}, {"lena"}),
    "Compras en Huánuco (pollo, hígado, verduras)": (
        {"arroz": 3, "pollo": 4, "higado_pollo": 6, "papa": 8, "huevo": 6, "zanahoria": 2, "cebolla": 3,
         "tomate": 2, "arveja_fresca": 1, "aceite": 6, "ajo": 1, "pan": 8, "palta": 1, "leche_evaporada": 1,
         "avena": 1, "azucar": 10}, {"gas", "refrigeradora"}),
    "Sin cocina encendida (solo pan y palta)": (
        {"pan": 8, "palta": 2, "platano": 4}, set()),
}
for nombre, (despensa, utensilios) in ESCENARIOS.items():
    t = time.time()
    r = recomendar(FAMILIA, despensa, utensilios, COMIDAS)
    print(f"\n=== {nombre}  ({time.time()-t:.1f} s)")
    for c in r["comidas"]:
        print(f"  {c['comida']:9} {c['receta']}")
        for p in c["porciones"]:
            print(f"     {p['persona']:22} {', '.join(p['items'])}")
    print("  Cobertura de energía:", ", ".join(f"{x['porcentaje']['energia_kcal']:.0f} %" for x in r["cobertura"]))
    print("  Hierro:", ", ".join(f"{x['porcentaje'].get('hierro_mg', 0):.0f} %" for x in r["cobertura"]))
    for a in r["avisos"]:
        print("  aviso:", a)
