"""Reglas de combinación y consejos. Solo usan ingredientes y utensilios disponibles."""

MENESTRAS = {"lentejas", "frejol", "habas", "arveja_seca", "garbanzo"}
FUENTES_VITAMINA_C = {"limon": "Exprime limón sobre las menestras o la ensalada: ayuda a absorber el hierro."}


def consejos_receta(receta, comida, despensa_ids, utensilios):
    ingredientes = {ing for c in receta["componentes"] for ing in c["por_unidad_g"]}
    consejos = []
    if ingredientes & MENESTRAS:
        for fuente, texto in FUENTES_VITAMINA_C.items():
            if fuente in despensa_ids:
                consejos.append(texto)
                break
        consejos.append("Si toman infusión o té, mejor 1 hora después de comer: reduce la absorción del hierro.")
    if comida == "cena" and "refrigeradora" not in utensilios:
        consejos.append("Sin refrigeradora: prepara solo lo de la noche y no guardes sobras para el día siguiente.")
    return consejos


def avisos_dia():
    return ["Cocina con sal yodada, en poca cantidad."]
