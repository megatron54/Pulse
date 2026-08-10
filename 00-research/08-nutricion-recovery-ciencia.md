# Investigación previa: nutrición ajustada por sueño/HRV/recovery (Épica I)

> Documento de investigación REQUERIDO antes de codificar ningún umbral del
> motor de nutrición ajustado por recovery (Épica I, `02-roadmap/
> 03-vision-produccion.md`) - mismo criterio que se exigió para
> `00-research/06-periodizacion-ciencia-deportiva.md` antes de escribir
> `engine/periodization.py`. Este documento NO implementa código: fija la
> evidencia real encontrada, dónde es sólida, dónde es contradictoria, y
> qué reglas serían defendibles vs. cuáles serían "falsa precisión"
> disfrazada de ciencia.

## Resumen ejecutivo (para no repetir esta investigación en el futuro)

La pregunta que motivó esta investigación: *¿puede un motor de reglas
determinista (Capa 1) ajustar de forma defendible el objetivo calórico/
macros usando datos crudos de sueño y HRV, no solo el semáforo categórico
de recovery que ya existe?*

**Respuesta corta: parcialmente sí, pero con umbrales mucho más
conservadores de lo que el pedido original sugería, y basados en
*comportamiento/composición corporal*, no en un mecanismo hormonal
específico** (la evidencia hormonal es la parte más débil y contradictoria
de toda la literatura revisada).

## 1. Sueño y apetito/ingesta calórica - evidencia MIXTA a nivel hormonal, más consistente a nivel de comportamiento

- **Gresser et al. 2025** (*Obesities*, MDPI, systematic review + meta-análisis, 6 RCTs, n=141): **NO encontró cambios significativos en ghrelin ni leptina** tras privación de sueño (ghrelin SMD −0.27, IC95% −1.00 a 0.46, p=0.47; leptina SMD 0.10, IC95% −0.22 a 0.42, p=0.53). Heterogeneidad alta en ghrelin (I²=83.8%). **Conclusión de los propios autores: la evidencia hormonal es inconsistente, contraria a la narrativa popular de "menos sueño → más ghrelina, menos leptina".**
- **Soltanieh et al. 2021** (*Clinical Nutrition ESPEN*, systematic review, 50 RCTs, n adultos+niños): sí encontró que la restricción de sueño se asocia a un **aumento significativo de ingesta calórica, ingesta de grasa, peso corporal, apetito, hambre, número de comidas y tamaño de las porciones** - pero **sin cambios significativos en ghrelina/leptina/cortisol séricos**. Es decir: el efecto de comportamiento (comer más) parece más robusto que el mecanismo hormonal propuesto para explicarlo.
- **Nedeltcheva/Penev et al. 2010** (*Annals of Internal Medicine*, RCT controlado, U. Chicago): con la MISMA restricción calórica, dormir 5.5h/noche vs. 8.5h/noche produjo la MISMA pérdida de peso total, pero **la composición cambió radicalmente**: con sueño adecuado, ~50% de la pérdida fue grasa; con sueño restringido, solo ~25% fue grasa (el resto, masa magra). Ghrelina más alta y más hambre reportada con sueño restringido. **Este es el hallazgo más sólido y accionable de toda la búsqueda**: el riesgo real de mal sueño sostenido en déficit no es "vas a comer descontroladamente", es "vas a perder más músculo que grasa por la misma pérdida de peso".

**Implicación para el motor de reglas**: un umbral que diga "si HRV/sueño bajan X%, reduce Y% las calorías asumiendo que subirá el apetito" **no está bien sostenido** - la evidencia hormonal que justificaría ese mecanismo es débil/contradictoria. Un umbral que diga "sueño pobre sostenido durante un déficit prolongado empeora la partición de la pérdida de peso hacia masa magra" **sí tiene una base más sólida** (RCT controlado, resultado de composición corporal medible, no solo un proxy hormonal).

## 2. HRV y déficit calórico - evidencia más débil, principalmente de fuentes secundarias

- Se encontró una afirmación repetida en fuentes secundarias (blogs de apps de recovery, ej. Cora) de que *"un estudio de 2020 en European Journal of Sport Science encontró que atletas en déficit calórico mostraban HRV significativamente más baja que en mantenimiento"*. **No se pudo verificar esta cita contra la fuente primaria en esta pasada de investigación** - se cita aquí como pista, NO como hecho confirmado. Antes de usar esto como base de un umbral, habría que localizar y leer el paper original.
- Lo que SÍ está bien establecido (consenso del COI, ver punto 3): la disponibilidad energética baja sostenida (no un solo día de déficit) es un factor de riesgo real para salud/rendimiento - y HRV/RHR alterados son señales conocidas de sobreentrenamiento/baja disponibilidad energética, coherente con el uso que Pulse YA hace de esas señales (semáforo de readiness), aunque no como disparador específico de un ajuste de macros.

## 3. RED-S / disponibilidad energética baja - consenso fuerte, pero es sobre *déficit crónico severo*, no sobre "un mal día de sueño"

- El consenso del Comité Olímpico Internacional (RED-S, 2018 y actualizaciones posteriores) es la pieza de evidencia MÁS sólida de toda esta investigación: la disponibilidad energética baja sostenida en atletas (de ambos sexos) produce disfunción metabólica, hormonal, ósea, inmune y de rendimiento reales y bien documentadas.
- **Importante para no sobre-generalizar**: RED-S es sobre déficits **crónicos y severos** (semanas/meses), típicamente en atletas de alto volumen de entrenamiento - no es evidencia de que "un HRV bajo puntual" o "una noche de mal sueño" deba disparar un ajuste automático de calorías. Es la justificación científica más fuerte para la regla YA EXISTENTE de "pausar el déficit tras varios días sostenidos de mal readiness" (`engine.guardrails.should_pause_calorie_deficit`), no para una regla nueva basada en un solo valor crudo.

## 4. Qué NO se puede defender con esta evidencia (evitar falsa precisión)

- **Un umbral tipo "si sleep_score < 70, reduce el déficit un 15%"**: no hay ningún estudio que dé ese número. Sería inventarse una cifra con apariencia de rigor científico que no existe - exactamente lo que el principio "nunca falsa precisión" de este proyecto prohíbe.
- **Un umbral de HRV puntual disparando un ajuste de macros específico** (ej. "%carbohidratos +X si HRV cae Y%"): no encontrado en la literatura revisada. La pista de Cora (no verificada) hablaría de un efecto general (déficit → HRV más baja), no de una regla de ajuste de macros en sentido inverso.
- **Cualquier regla que use el mecanismo "sueño → ghrelina/leptina → hambre"** como justificación: la evidencia de ese mecanismo específico es la más débil de toda la búsqueda (meta-análisis 2025 sin significancia).

## 5. Qué SÍ sería defendible, con umbrales conservadores y auditables (propuesta para la fase de implementación, no implementada todavía)

Basado únicamente en lo que la evidencia sostiene con más fuerza:

1. **Regla de composición, no de apetito**: si el usuario lleva **sueño pobre sostenido (ej. ≥3 noches con `sleep_score` bajo, umbral exacto por decidir con el usuario, no inventado aquí) DURANTE una fase de déficit (`fase_peso_actual == cut`) ya activa**, la explicación al usuario (Capa 3) debería mencionar el riesgo real y documentado (peor partición grasa/músculo, no "vas a tener más hambre") - y opcionalmente reducir la agresividad del déficit (nunca eliminarlo del todo automáticamente, igual que la regla ya existente de guardrails).
2. **Esto es una EXTENSIÓN de la regla ya existente** (`should_pause_calorie_deficit`, basada en readiness categórico 3 días seguidos), no una regla nueva independiente - añadiría `sleep_score` crudo sostenido como una señal adicional, con la MISMA filosofía conservadora (pausar/suavizar, nunca inventar un ajuste "positivo" audaz sin evidencia).
3. **HRV cruda**: dada la debilidad de la evidencia encontrada (una sola fuente secundaria no verificada), **no se recomienda** construir ningún umbral nuevo basado en HRV cruda todavía. Si en el futuro se localiza y verifica la fuente primaria mencionada en el punto 2, revisar esta recomendación.
4. **Nunca en dirección de "aflojar" el déficit por buen HRV/sueño de forma automática sin supervisión**: la evidencia de esta investigación es toda sobre RIESGOS de mal sueño/déficit, no sobre "cuándo es seguro ser más agresivo" - cualquier regla en esa dirección necesitaría su propia investigación separada.

## 6. Relación con la Épica 13 del roadmap (timing/ayuno intermitente) - reconfirmado

Como ya se documentó en el punto 7 de `03-vision-produccion.md`: esta investigación es sobre **cuánto** (cantidad calórica/composición), la Épica 13 es sobre **cuándo** (timing/ayuno). Comparten el principio de "Capa 1 decide con umbrales conservadores, Capa 3 explica", pero son motores distintos. Esta investigación NO cubre timing y no debe usarse como base para reglas de ayuno intermitente.

## 7. Decisión pendiente antes de escribir código (Épica I)

Los umbrales concretos (cuántas noches de sueño pobre, qué `sleep_score` cuenta como "pobre", cuánto reducir la agresividad del déficit) **no se fijan en este documento** - son una decisión de producto/seguridad que debe tomarse explícitamente con el usuario antes de codificarla (mismo criterio que motivó pedir confirmación antes de cualquier regla de salud en este proyecto), no algo que un agente de IA deba inventar unilateralmente. Este documento entrega la evidencia; la siguiente sesión que retome la Épica I debe: (a) confirmar los umbrales con el usuario, (b) implementarlos en `engine/` (Capa 1, determinista, testeado), (c) exponer la traza de qué regla disparó vía `AuditLog` (mismo patrón que `should_pause_calorie_deficit`), (d) conectar la explicación en Capa 3 vía `generate_context_narrative` (ya construido en la Épica H).

## Fuentes citadas

- Gresser D, McLimans K, Lee S, Morgan-Bathke M. "The Impact of Sleep Deprivation on Hunger-Related Hormones: A Meta-Analysis and Systematic Review." *Obesities* 2025;5:48. https://doi.org/10.3390/obesities5020048
- Soltanieh S, Solgi S, Ansari M, Santos HO, Abbasi B. "Effect of sleep duration on dietary intake, desire to eat, measures of food intake and metabolic hormones: A systematic review of clinical trials." *Clinical Nutrition ESPEN* 2021;45:55-65. https://doi.org/10.1016/j.clnesp.2021.07.029
- Nedeltcheva AV, Kilkus JM, Imperial J, Schoeller DA, Penev PD. "Insufficient sleep undermines dietary efforts to reduce adiposity." *Annals of Internal Medicine* 2010;153(7):435-441 (resumen vía University of Chicago News, oct 2010).
- Comité Olímpico Internacional. Consenso RED-S (Relative Energy Deficiency in Sport), 2018 y actualizaciones - referencia general vía múltiples fuentes secundarias médicas revisadas (BJGP, ScienceDirect, PubMed 32902400).
- Cora App blog, "Nutrition for Recovery" (2026) - cita un estudio de 2020 en *European Journal of Sport Science* sobre déficit calórico y HRV. **No verificado contra la fuente primaria** - solo mencionado como pista para investigación futura, no como evidencia confirmada.
