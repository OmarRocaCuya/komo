"""Requerimientos diarios por persona.

Energía: gasto en reposo (ecuaciones de Schofield adoptadas por FAO/OMS/UNU 2004)
multiplicado por el nivel de actividad del día. Gestación y lactancia suman su
requerimiento adicional.

TODOS los valores de referencia de este archivo son PROVISIONALES para el
prototipo. Jazmín debe validarlos o reemplazarlos antes de usar Komo en campo.
Cada tabla indica su fuente para facilitar la revisión.
"""

from dataclasses import dataclass, field

NUTRIENTES = ["energia_kcal", "proteina_g", "hierro_mg", "zinc_mg", "calcio_mg", "vitamina_a_ug", "vitamina_c_mg"]

# Ecuaciones de Schofield (FAO/OMS/UNU 2004, Human energy requirements, cuadro 5.2).
# Gasto energético en reposo en kcal/día = a * peso_kg + b
SCHOFIELD = {
    "h": [(3, 59.512, -30.4), (10, 22.706, 504.3), (18, 17.686, 658.2),
          (30, 15.057, 692.2), (60, 11.472, 873.1), (200, 11.711, 587.7)],
    "m": [(3, 58.317, -31.1), (10, 20.315, 485.9), (18, 13.384, 692.6),
          (30, 14.818, 486.6), (60, 8.126, 845.6), (200, 9.082, 658.5)],
}

# Factor de actividad (PAL). Adultos: punto medio de los rangos FAO/OMS/UNU 2004
# (1,40-1,69 / 1,70-1,99 / 2,00-2,40). Niños y adolescentes: PROVISIONAL.
PAL = {
    "nino": {"ligera": 1.45, "moderada": 1.60, "intensa": 1.75},        # 3 a 9 años
    "adolescente": {"ligera": 1.50, "moderada": 1.75, "intensa": 2.00},  # 10 a 17 años
    "adulto": {"ligera": 1.55, "moderada": 1.85, "intensa": 2.20},       # 18 años o más
}

# Menores de 3 años: energía por kg (aprox. FAO/OMS/UNU 2004). PROVISIONAL.
KCAL_POR_KG_1_A_2 = {"h": 82.0, "m": 80.0}

# Adicionales por gestación (2.º trimestre, porque la app no pregunta el trimestre)
# y por lactancia (primeros 6 meses). FAO/OMS/UNU 2004 y OMS 2007.
EXTRA = {
    "gestando": {"energia_kcal": 285, "proteina_g": 9},
    "lactancia": {"energia_kcal": 505, "proteina_g": 19},
}

# Peso de referencia en menores de 18 años: mediana aproximada de peso para la edad
# (OMS). PROVISIONAL: reemplazar por la tabla oficial OMS que use el MINSA.
PESO_REF_MENORES = {
    "h": {1: 9.6, 2: 12.2, 3: 14.3, 4: 16.3, 5: 18.3, 6: 20.5, 7: 22.9, 8: 25.4, 9: 28.1,
          10: 31.2, 11: 35.6, 12: 39.9, 13: 45.3, 14: 50.8, 15: 56.0, 16: 60.8, 17: 64.4},
    "m": {1: 8.9, 2: 11.5, 3: 13.9, 4: 16.1, 5: 18.2, 6: 20.2, 7: 22.4, 8: 25.0, 9: 28.2,
          10: 31.9, 11: 36.9, 12: 41.5, 13: 45.8, 14: 49.4, 15: 52.1, 16: 53.5, 17: 54.4},
}

# Talla de referencia en adultos cuando no se midió (cm). PROVISIONAL.
TALLA_REF_ADULTO = {"h": 165.0, "m": 152.0}
IMC_REFERENCIA = 22.0

# Proteína segura por kg (OMS/FAO/UNU 2007, aproximado). PROVISIONAL.
def proteina_por_kg(edad):
    if edad < 2:
        return 1.14
    if edad < 3:
        return 0.97
    if edad < 11:
        return 0.92
    if edad < 15:
        return 0.90
    if edad < 18:
        return 0.87
    return 0.83

# Micronutrientes (FAO/OMS 2004, Vitamin and mineral requirements). PROVISIONAL.
# Hierro con biodisponibilidad del 10 %, típica de dietas basadas en cereales y menestras.
def micronutrientes(edad, sexo, estado):
    if edad < 4:
        base = {"hierro_mg": 5.8, "zinc_mg": 4.1, "calcio_mg": 500, "vitamina_a_ug": 400, "vitamina_c_mg": 30}
    elif edad < 7:
        base = {"hierro_mg": 6.3, "zinc_mg": 4.8, "calcio_mg": 600, "vitamina_a_ug": 450, "vitamina_c_mg": 30}
    elif edad < 11:
        base = {"hierro_mg": 8.9, "zinc_mg": 5.6, "calcio_mg": 700, "vitamina_a_ug": 500, "vitamina_c_mg": 35}
    elif edad < 18:
        if sexo == "h":
            base = {"hierro_mg": 14.6 if edad < 15 else 18.8, "zinc_mg": 8.6, "calcio_mg": 1300,
                    "vitamina_a_ug": 600, "vitamina_c_mg": 40}
        else:
            base = {"hierro_mg": 32.7 if edad < 15 else 31.0, "zinc_mg": 7.2, "calcio_mg": 1300,
                    "vitamina_a_ug": 600, "vitamina_c_mg": 40}
    else:
        if sexo == "h":
            base = {"hierro_mg": 13.7, "zinc_mg": 7.0, "calcio_mg": 1000 if edad < 65 else 1300,
                    "vitamina_a_ug": 600, "vitamina_c_mg": 45}
        else:
            base = {"hierro_mg": 29.4 if edad < 51 else 11.3, "zinc_mg": 4.9,
                    "calcio_mg": 1000 if edad < 51 else 1300, "vitamina_a_ug": 500, "vitamina_c_mg": 45}
    if estado == "gestando":
        base.update({"zinc_mg": 7.3, "calcio_mg": 1200, "vitamina_a_ug": 800, "vitamina_c_mg": 55})
    elif estado == "lactancia":
        base.update({"hierro_mg": 15.0, "zinc_mg": 7.2, "calcio_mg": 1000, "vitamina_a_ug": 850, "vitamina_c_mg": 70})
    return base

# Reparto del requerimiento diario por comida. PROVISIONAL (el 10 % restante
# corresponde a refrigerios, fuera del MVP).
REPARTO_COMIDAS = {"desayuno": 0.25, "almuerzo": 0.40, "cena": 0.25}


@dataclass
class Persona:
    edad: int
    sexo: str            # "m" mujer, "h" hombre
    actividad: str       # "ligera", "moderada", "intensa"
    estado: str = "no"   # "no", "gestando", "lactancia"
    peso: float | None = None
    talla: float | None = None
    etiqueta: str = ""

    def descripcion(self):
        if self.etiqueta:
            return self.etiqueta
        sexo = "Mujer" if self.sexo == "m" else "Hombre"
        return f"{sexo}, {self.edad} {'año' if self.edad == 1 else 'años'}"


@dataclass
class Requerimiento:
    persona: Persona
    peso_usado: float
    origen_peso: str
    diario: dict = field(default_factory=dict)
    avisos: list = field(default_factory=list)


def _schofield(edad, sexo, peso):
    for limite, a, b in SCHOFIELD[sexo]:
        if edad < limite:
            return a * peso + b
    raise ValueError("edad fuera de rango")


def peso_para_calculo(p: Persona):
    """Devuelve (peso_kg, origen). Ver 'Decisiones de cálculo' en el documento de alcance."""
    if p.edad < 18:
        return PESO_REF_MENORES[p.sexo][max(1, p.edad)], "referencia por edad y sexo"
    if p.peso and p.talla:
        imc = p.peso / (p.talla / 100) ** 2
        if 18.5 <= imc <= 24.9:
            return float(p.peso), "medido"
        return IMC_REFERENCIA * (p.talla / 100) ** 2, f"referencia por talla (IMC medido {imc:.1f})"
    talla = p.talla or TALLA_REF_ADULTO[p.sexo]
    return IMC_REFERENCIA * (talla / 100) ** 2, "referencia por talla" if p.talla else "referencia por sexo"


def calcular(p: Persona) -> Requerimiento:
    if p.edad < 1:
        raise ValueError("Menores de 1 año: Komo no calcula porciones; seguir indicaciones del establecimiento de salud.")
    if p.sexo not in ("m", "h") or p.actividad not in ("ligera", "moderada", "intensa"):
        raise ValueError("Sexo o actividad no válidos.")
    peso, origen = peso_para_calculo(p)
    avisos = []
    if p.edad < 3:
        energia = KCAL_POR_KG_1_A_2[p.sexo] * peso
    else:
        grupo = "nino" if p.edad < 10 else ("adolescente" if p.edad < 18 else "adulto")
        energia = _schofield(p.edad, p.sexo, peso) * PAL[grupo][p.actividad]
    proteina = proteina_por_kg(p.edad) * peso
    estado = p.estado if (p.sexo == "m" and 12 <= p.edad <= 50) else "no"
    if estado in EXTRA:
        energia += EXTRA[estado]["energia_kcal"]
        proteina += EXTRA[estado]["proteina_g"]
    if estado == "gestando":
        avisos.append("Gestante: el hierro y el ácido fólico se cubren con la suplementación del establecimiento de salud.")
    diario = {"energia_kcal": energia, "proteina_g": proteina}
    diario.update(micronutrientes(p.edad, p.sexo, estado))
    return Requerimiento(persona=p, peso_usado=peso, origen_peso=origen, diario=diario, avisos=avisos)
