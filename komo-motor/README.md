# Komo · Prototipo del motor de sustitución

Prototipo en Python del cálculo de porciones de Komo. Sirve para validar la lógica con Jazmín **antes** de construir la app, y como referencia para que Jhoan la traduzca al stack final.

> Estado: prototipo. Los valores nutricionales vienen de las Tablas peruanas (CENAN/INS, 2017) y los pesos de las medidas caseras de las Tablas auxiliares (CENAN/INS, 2016). Los requerimientos y las recetas son **provisionales** hasta que Jazmín los valide.

## Cómo ejecutarlo

```bash
pip install scipy numpy pytest
python3 ejemplo.py        # la familia del diseño de Komo
python3 escenarios.py     # 4 despensas típicas de Churubamba
python3 -m pytest -q      # 46 pruebas
```

`salida_ejemplo.txt` y `salida_escenarios.txt` contienen los resultados.

## Qué hace

```python
from komo import Persona, recomendar

familia = [Persona(edad=38, sexo="h", actividad="intensa", peso=64, talla=162),
           Persona(edad=34, sexo="m", actividad="moderada", estado="lactancia"),
           Persona(edad=11, sexo="h", actividad="intensa"),
           Persona(edad=6, sexo="m", actividad="ligera")]
despensa = {"arroz": 2, "papa": 6, "lentejas": 1, "huevo": 4, "zanahoria": 2,
            "cebolla": 1, "ajo": 1, "limon": 3, "aceite": 3}   # en medidas caseras
r = recomendar(familia, despensa, {"lena", "batan"}, ["desayuno", "almuerzo", "cena"])
```

1. **Requerimiento por persona** (`requerimientos.py`): gasto en reposo con las ecuaciones de Schofield (FAO/OMS/UNU 2004) × nivel de actividad del día, más gestación o lactancia. Menores de 18 usan peso de referencia; adultos usan su peso solo si su IMC está entre 18,5 y 24,9.
2. **Recetas posibles**: se descartan las que necesitan un ingrediente o un utensilio que no hay. Los ingredientes `opcionales` (el limón de la ensalada) se quitan si no están.
3. **Equidad**: un primer modelo lineal calcula la fracción `t` de energía que **todos** pueden recibir por igual con la despensa. Si no alcanza, la escasez se reparte en la misma proporción.
4. **Calidad**: un segundo modelo, sin bajar de `t`, reparte cada persona entre comidas, cuida la proteína (también con equidad), los micronutrientes y el límite de grasa. Cada persona recibe el plato completo: cada componente puede ir de 65 % a 135 % de la proporción de la receta. Los acompañantes ricos en hierro (sangrecita, hígado) tienen `proporcion_min` 25 %, para que una cantidad pequeña no limite el plato.
5. **Elección de platos**: se preseleccionan las 3 mejores recetas por comida y se prueban sus combinaciones. Entre las que quedan a menos de 3 puntos de la mejor cobertura, gana la que, ya redondeada, no deja a nadie sin una parte del plato (por ejemplo, sin huevo).
6. **Redondeo a medidas caseras**: nunca supera la despensa; lo que sobra va a quien tiene menor cobertura, y nadie se queda sin un componente mientras otro recibe dos medidas (con huevos: todos reciben uno antes de que alguien reciba dos).
7. **Condimentos flexibles** (aceite, ajo, limón, azúcar, ají): se usa lo que alcance y nunca bloquean un plato.
8. **Consejos** (`reglas.py`): solo con lo disponible (limón si hay limón; no guardar sobras si no hay refrigeradora).

La despensa es **una sola para todo el día**: lo que usa el desayuno ya no está para el almuerzo.

## Resultado del ejemplo

| Comida | Plato elegido | Porciones (padre · madre · niño 11 · niña 6) |
| --- | --- | --- |
| Desayuno | Papa sancochada con huevo revuelto | 1 ½ papas y 1 huevo · ½ y 1 · 1 ½ y 1 · 1 y 1 |
| Almuerzo | Lentejas con arroz y ensalada | arroz 2 ¼, 1 ¾, 1 ½, ½ tazas · lentejas ¾, 1 ¼, ½, ¼ taza |
| Cena | Sopa de papa con arroz y verduras | 1 ½ · 1 · 1 · 1 cucharones |

La despensa cubre cerca del **46 %** de la energía que la familia necesita en esas 3 comidas. Komo lo reparte por igual (44 % a 52 % por persona tras redondear) y avisa que el calcio y la vitamina C quedan bajos. La madre recibe más lentejas porque da de lactar: su requerimiento de proteína es mayor.

## Catálogo de la zona (borrador para Jazmín)

`alimentos.json` tiene **45 ingredientes**: los 11 del prototipo y **34 de la zona** (papa blanca, olluco, oca, camote, yuca, papa seca, mote, choclo, trigo, avena, pan, habas, arveja, frejol, cuy, pollo, hígado de pollo y de res, sangrecita, atún, trucha, leches, zapallo, col, tomate, ají amarillo, frutas y azúcar). Cada uno tiene su código CENAN y el peso neto de su medida casera con el código de las Tablas auxiliares. La medida de la sangrecita es **provisional**: no está en las Tablas auxiliares.

`recetas.json` tiene **24 recetas**: 7 de prueba y **17 borradores** con `"estado": "borrador"` y `nota_validacion`:

| Desayuno | Almuerzo | Cena |
| --- | --- | --- |
| Avena con leche y pan · Mote con queso · Habas con queso · Camote con huevo · Pan con palta (sin cocina) · Quinua caliente con pan | Cuy guisado con papa · Arroz con pollo · Frejol con arroz · Hígado encebollado con papa · Trucha frita con papa · Locro de zapallo · Sopa de trigo con habas | Sopa de quinua · Olluquito con arroz · Sangrecita con papa · Tortilla de verduras con arroz · Caldo de mote con habas |

Los pesos marcados como **Estimado** (sopas, locro, mote cocido, avena) deben pesarse en campo o en la prueba interna de noviembre.

**Escenarios** (`escenarios.py`, misma familia, 3 comidas):

| Despensa | Platos | Energía cubierta |
| --- | --- | --- |
| Chacra en cosecha (papa, habas, mote, cuy) | Mote con queso · Cuy con papa · Sopa de quinua | ≈ 38 % |
| Fin de mes (arroz, frejol, papa, sangrecita) | Avena con pan · Frejol con arroz · Sangrecita con papa | ≈ 48 %, hierro sobre 100 % |
| Compras en Huánuco (pollo, hígado, verduras) | Avena con pan · Hígado con papa · Tortilla con arroz | ≈ 76 % |
| Sin cocina encendida | Pan con palta; avisa que no hay almuerzo ni cena posibles | ≈ 47 % |

## Hallazgos que afectan al producto

1. **La escasez es el caso normal, no la excepción.** Con una despensa realista, Komo no puede prometer "comer completo". La app debe decir qué parte cubre y repartirla con justicia. Propuesta: mostrar en la pantalla de platos un aviso como el de `avisos[0]`.
2. **La regla de reparto es una decisión del equipo, no técnica.** El prototipo reparte en la misma proporción para todos. Jazmín y Brenda deben decidir si en escasez se prioriza a niños, gestantes y madres que dan de lactar; el modelo puede hacerlo cambiando la restricción de equidad por pesos.
3. **El tamaño máximo del plato limita a los más activos.** Un adulto con actividad intensa (≈3 500 kcal) no llega con 3 comidas de porciones razonables, aun con comida de sobra. El motor lo distingue de la falta de comida y sugiere un refrigerio o fiambre; refuerza la idea de sumar refrigerios después del MVP.
4. **El calcio siempre sale bajo** sin lácteos ni menestras ricas en calcio, y el **hierro** de mujeres en edad fértil y adolescentes no se cubre solo con dieta: el mensaje debe derivar a la suplementación del establecimiento de salud.
5. **La anemia orienta el catálogo.** En Churubamba se reportó 55,9 % de anemia (2016). Con sangrecita o hígado, el motor da más a quien más hierro necesita (la madre que da de lactar) sin que el equipo lo programe aparte.
6. **Las lentejas de la tabla peruana rinden menos energía** (211 kcal/100 g) que las tablas internacionales, porque el CENAN calcula con carbohidratos disponibles y separa la fibra. Usar siempre la tabla peruana.

## Para Jazmín: qué validar

| Archivo | Qué revisar |
| --- | --- |
| `komo/requerimientos.py` | Factores de actividad de niños y adolescentes, pesos de referencia por edad (reemplazar por la tabla OMS oficial), extras de gestación y lactancia, proteína por kg, micronutrientes y reparto por comida (25 % · 40 % · 25 %) |
| `herramientas/generar_alimentos.py` | Código CENAN elegido para cada ingrediente y **gramos por medida casera** (Módulo I de las Tablas auxiliares 2016); confirmar que los 34 ingredientes de la zona son los que se consiguen en Churubamba |
| `komo/datos/recetas.json` | Las 17 recetas `borrador`: si son platos de la zona, gramos crudos por medida servida (factores crudo a cocido del Módulo II), proporción base, tamaño máximo y utensilios |
| `komo/reglas.py` | Textos y condiciones de los consejos |

## Para Jhoan: notas de implementación

- `komo/datos/tablas_cenan_2017.json` tiene **922 alimentos** extraídos del PDF del CENAN con `herramientas/extraer_cenan.py` (24 columnas por alimento). La tabla reporta 928; 6 filas con formato irregular y las preparaciones (grupo S) no se extrajeron.
- El modelo es lineal y pequeño (≈100 a 300 variables). Resolverlo en el teléfono, sin conexión, es viable; en JavaScript puede evaluarse un solver como HiGHS compilado a WebAssembly o javascript-lp-solver. La lógica de `motor.py` se traduce casi línea por línea.
- **Rendimiento**: se preseleccionan las 3 mejores recetas por comida (27 combinaciones como máximo). Con 24 recetas reales responde en menos de 1 s; con un catálogo de 125 recetas, en cerca de 1 s.
- La salida de `recomendar()` ya tiene la forma de las pantallas: platos por comida, porciones por persona en medidas caseras, ingredientes para cocinar, consejos, cobertura y avisos.

## Estructura

```
komo/
  requerimientos.py      requerimiento diario por persona
  motor.py               filtro de recetas, modelos de equidad y calidad, redondeo
  reglas.py              consejos según despensa y utensilios
  datos/
    alimentos.json       45 ingredientes (generado desde la tabla CENAN)
    tablas_cenan_2017.json  922 alimentos de las Tablas peruanas 2017
    recetas.json         7 recetas de prueba y 17 borradores de la zona
    factores_coccion_cenan_2016.json  213 factores crudo a cocido (Módulo II)
herramientas/
  extraer_cenan.py       PDF del CENAN (texto) → JSON
  generar_alimentos.py   tabla CENAN → alimentos.json
tests/test_motor.py      46 pruebas
ejemplo.py               familia del diseño
escenarios.py            4 despensas típicas de Churubamba
```

## Fuentes

- Tablas peruanas de composición de alimentos, 10.ª ed. CENAN/INS, 2017.
- Tablas auxiliares para la formulación y evaluación de regímenes alimentarios, 2.ª ed. CENAN/INS, 2016.
- FAO/WHO/UNU. Human energy requirements. 2004.
- WHO/FAO/UNU. Protein and amino acid requirements in human nutrition. 2007.
- FAO/WHO. Vitamin and mineral requirements in human nutrition. 2004.
- Ibazeta-Estela y Penadillo-Contreras. Rev Peru Investig Salud, 2019 (anemia y conocimiento materno, Churubamba).
- INEI. ENDES 2024 (anemia en menores de 3 años: 43,7 %).
