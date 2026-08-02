# Periodización multi-objetivo: fuerza + hipertrofia + resistencia + artes marciales + peso

## El "interference effect" del entrenamiento concurrente

- **Wilson et al. 2012** ([pubmed 22002517](https://pubmed.ncbi.nlm.nih.gov/22002517/)): confirma interferencia real en fuerza/hipertrofia/potencia al añadir resistencia, dependiente del volumen aeróbico.
- **Lundberg et al. 2022** ([pubmed 35476184](https://pubmed.ncbi.nlm.nih.gov/35476184/)): la hipertrofia global **no se ve negativamente afectada** por entrenamiento concurrente si el volumen de fuerza se mantiene adecuado.
- **Held et al. 2026** (umbrella review, [pubmed 41762427](https://pubmed.ncbi.nlm.nih.gov/41762427/)): interferencia real pero modesta y manejable con buen diseño de dosis/secuencia/recuperación.
- **Ferraro-Farro et al. 2026** ([pubmed 41734815](https://pubmed.ncbi.nlm.nih.gov/41734815/)): sprint interval training interfiere **menos** que cardio continuo de baja intensidad.

### Reglas prácticas de secuenciación
1. Separar sesiones ≥6-8h cuando sea posible (AM/PM si es el mismo día).
2. Si van en la misma sesión: entrenar primero la cualidad **prioritaria del bloque actual**.
3. Preferir HIIT/sprints cortos sobre cardio continuo largo cuando compite con fuerza.
4. Nunca apilar 3 sistemas de alta demanda neuromuscular el mismo día (fuerza pesada + sprints + sparring intenso).
5. Artes marciales = tercera "pierna" del triángulo de interferencia (CNS + metabólico + destreza motora), no subsumir en "cardio".

## Modelo de periodización recomendado

**Conjugado-ondulante híbrido:**
- Estructura semanal fija de "slots" por cualidad (ej. 2 fuerza, 2 artes marciales, 2 resistencia, 1 descanso activo).
- DUP (ondulación diaria/semanal) dentro de cada slot.
- Microciclos de 3-4 semanas + semana de descarga (deload) cada 4ª semana.
- Bloques de énfasis rotativo de 4-6 semanas: 1 cualidad prioritaria + resto en mantenimiento (60-70% del volumen normal). **Nunca maximizar todo a la vez.**

## Gestión de fatiga con datos de Garmin

- **Di, Hongye & Donglin 2025** ([PMC12859854](https://pmc.ncbi.nlm.nih.gov/articles/PMC12859854/)): sistema autorregulado en tiempo real con HRV + "performance load ratio" mejora adaptabilidad vs. carga fija.
- **Williams et al. 2020** ([PMC7795557](https://pmc.ncbi.nlm.nih.gov/articles/PMC7795557/)): HRV por smartphone detecta bien cambios de carga si se mide en condiciones estandarizadas.
- **Regla operativa**: usar **tendencia de 3-7 días vs. baseline personal de 4-6 semanas**, nunca el valor absoluto de un solo día.

## Cortes de peso y recomposición

- **Garthe et al. 2011** ([pubmed 21558571](https://pubmed.ncbi.nlm.nih.gov/21558571/)): pérdida de peso a 0.7%/semana preserva significativamente más masa magra que 1.4%/semana, con igual pérdida de grasa total. **Regla: 0.5-0.7% peso corporal/semana** en atletas con componente de fuerza.
- **Campbell et al. 2020** ([pubmed 33467235](https://pubmed.ncbi.nlm.nih.gov/33467235/)): restricción calórica intermitente (ciclada) preserva más masa libre de grasa que restricción continua a igual déficit promedio.
- **Aplicación práctica**: en semanas de doble sesión, mantenimiento o superávit leve; en días de sesión única/descanso, déficit más marcado.

## Motor de reglas (pseudocódigo implementable)

Ver implementación completa y comentada más abajo. Lógica núcleo:

1. **Semáforo de readiness diario** (RED/YELLOW/GREEN) a partir de HRV vs baseline, Training Readiness, Body Battery, ACWR, sueño, dolor articular.
2. **RED** → descanso o sesión muy ligera/técnica, nunca sparring duro ni fuerza pesada.
3. **YELLOW** → reducir volumen 30-50%, cap de RPE en 7, evitar fallo muscular.
4. **GREEN** → seguir plan, pero si es día de doble sesión, separar ≥6h y priorizar la cualidad dominante del bloque.
5. **Ajuste semanal de volumen** estilo APRE/RP: subir ~10% en la cualidad prioritaria si RPE bajo y buena recuperación; bajar ~20% si RPE alto o soreness elevado; cualidades en mantenimiento nunca suben, solo se protege el MEV (Minimum Effective Volume).
6. **Reglas duras no negociables**: dolor articular → descanso total sin excepción. ACWR>1.5 dos días seguidos → deload inmediato. Fase de corte + RED 3 días seguidos → pausar el déficit a mantenimiento.

```python
def compute_readiness_score(ctx) -> str:
    """RED / YELLOW / GREEN a partir de HRV, Training Readiness,
    Body Battery, ACWR, sueño y dolor articular."""
    red_flags = yellow_flags = 0
    hrv_delta_pct = (ctx.hrv_today - ctx.hrv_baseline_28d) / ctx.hrv_baseline_28d
    if hrv_delta_pct < -0.15 or ctx.hrv_trend_7d < -0.10: red_flags += 1
    elif hrv_delta_pct < -0.07: yellow_flags += 1
    if ctx.training_readiness == "very_low": red_flags += 1
    elif ctx.training_readiness == "low": yellow_flags += 1
    if ctx.body_battery_am < 30: red_flags += 1
    elif ctx.body_battery_am < 50: yellow_flags += 1
    if ctx.acwr > 1.5: red_flags += 1
    elif ctx.acwr > 1.3: yellow_flags += 1
    if ctx.sleep_score < 50: yellow_flags += 1
    if ctx.joint_pain_flag: red_flags += 1
    if red_flags >= 1: return "RED"
    if yellow_flags >= 2: return "YELLOW"
    return "GREEN"
```

(Pseudocódigo completo de `select_session_type`, `adjust_weekly_volume`, `nutrition_decision` y `weekly_block_rotation` disponible en el chat de investigación original — se trasladará al módulo `engine/periodization.py` en la fase de implementación.)

## Fuentes principales
- Wilson 2012: https://pubmed.ncbi.nlm.nih.gov/22002517/
- Lundberg 2022: https://pubmed.ncbi.nlm.nih.gov/35476184/
- Held 2026: https://pubmed.ncbi.nlm.nih.gov/41762427/
- Ferraro-Farro 2026: https://pubmed.ncbi.nlm.nih.gov/41734815/
- Di/Hongye/Donglin 2025: https://pmc.ncbi.nlm.nih.gov/articles/PMC12859854/
- Williams 2020: https://pmc.ncbi.nlm.nih.gov/articles/PMC7795557/
- Garthe 2011: https://pubmed.ncbi.nlm.nih.gov/21558571/
- Campbell 2020: https://pubmed.ncbi.nlm.nih.gov/33467235/
- Ibrahim/Beaumont/Strohacker 2024 (scoping review autorregulación): https://pmc.ncbi.nlm.nih.gov/articles/PMC11042849/
