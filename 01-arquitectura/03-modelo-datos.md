# Modelo de datos (borrador inicial)

> Nota: wger ya aporta buena parte del esquema de `workouts`, `exercises` y `nutrition_plans`. Este documento cubre las tablas ADICIONALES que hay que construir encima.

## Entidades nuevas necesarias

### `user_profile`
- objetivos_activos (JSON: lista de {tipo, prioridad, fecha_inicio})
- lesiones_activas (JSON: lista de {zona, severidad, fecha, notas})
- fase_peso_actual (enum: cut | maintenance | recomp | surplus)
- altura_cm, fecha_nacimiento, sexo (para fórmulas Navy/TDEE)
- bloque_periodizacion_actual (referencia a `training_blocks`)

### `garmin_daily_metrics` (append-only, histórico inmutable)
- fecha, hrv_status, hrv_value, body_battery_am, training_readiness, sleep_score, vo2max, stress_avg, resting_hr

### `garmin_activities`
- activity_id (Garmin), fecha, tipo, duración, distancia, hr_avg, hr_max, training_effect, raw_json (payload completo por si se necesita reprocesar)

### `body_measurements` (append-only)
- fecha, peso_kg, cuello_cm, cintura_cm, cadera_cm, bodyfat_pct_estimado, bodyfat_pct_rango_min, bodyfat_pct_rango_max, metodo (navy | navy+pose | manual)

### `progress_photos`
- fecha, ángulo (frontal|lateral|espalda), ruta_cifrada_local, landmarks_json (output de MediaPipe, no la foto en sí se usa después)

### `training_blocks`
- fecha_inicio, fecha_fin, objetivo_prioritario, objetivos_mantenimiento (JSON), semana_actual, es_deload (bool)

### `readiness_log` (append-only, una fila por día)
- fecha, hrv_delta_pct, training_readiness, body_battery_am, acwr, sleep_score, joint_pain_flag, resultado (RED|YELLOW|GREEN), sesion_recomendada, volumen_pct_ajustado

### `nutrition_log`
- fecha, comida (desayuno|comida|cena|snack), fuente (manual|foto_ia|barcode_off), alimentos (JSON), macros_estimados (kcal, prot, carbs, grasa), confirmado_por_usuario (bool)

### `coach_conversations`
- thread_id, timestamp, rol (user|coach), mensaje, decision_tipada_asociada (referencia opcional a la decisión del motor de reglas que originó la respuesta), modelo_usado

### `audit_log` (motor de reglas — trazabilidad completa)
- timestamp, modulo (nutrition|progression|periodization|guardrails), inputs_json, regla_disparada, output, decision_final

## Principios del esquema

1. **Append-only para todo lo temporal**: nunca UPDATE sobre mediciones, actividades o logs — siempre INSERT nuevo con timestamp. Permite reconstruir tendencias reales y auditar el motor de reglas.
2. **Separación clara entre "lo que wger ya modela" y "lo nuevo"**: se extiende wger vía tablas propias relacionadas por `user_id`/`workout_id`, no se modifica el núcleo de wger (facilita actualizar wger sin conflictos).
3. **`raw_json` en las tablas de ingesta externa** (Garmin, fotos): guardar siempre el payload crudo además de los campos parseados, para poder reprocesar si cambia la lógica de negocio sin tener que re-sincronizar con Garmin.
