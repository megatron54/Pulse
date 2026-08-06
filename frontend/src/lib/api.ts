/**
 * Cliente tipado de la API de Pulse (Fase A, backend/api/).
 *
 * Sin lógica de negocio aquí: solo llamadas HTTP tipadas. Todas las
 * decisiones (macros, readiness, sesión) ya vienen calculadas por el
 * backend - el frontend nunca decide nada, solo muestra y envía datos.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // respuesta sin JSON (ej. 500 sin body) - se usa statusText
    }
    throw new ApiError(res.status, detail);
  }
  // 204 / respuestas vacías
  const text = await res.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

/**
 * Fecha de HOY en la zona horaria LOCAL del usuario (no UTC).
 * `new Date().toISOString().slice(0,10)` da la fecha en UTC, que puede
 * desfasarse un día respecto a lo que el usuario percibe como "hoy"
 * (ej. medianoche pasada en horario de verano europeo) - crítico para
 * un tracker diario donde el día importa (readiness, macros, sesión).
 */
export function todayLocalDate(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export type User = {
  id: number;
  nombre: string;
  altura_cm: number;
  fecha_nacimiento: string;
  sexo: "M" | "F";
  fase_peso_actual: "cut" | "maintenance" | "recomp" | "surplus";
};

export type UserCreateInput = Omit<User, "id">;

export type BodyMeasurement = {
  id: number;
  fecha: string;
  peso_kg: number;
  metodo: "manual" | "navy" | "navy_pose";
  bodyfat_pct_rango_min: number | null;
  bodyfat_pct_rango_max: number | null;
};

export type BodyMeasurementInput = {
  target_date: string;
  peso_kg: number;
  cuello_cm?: number;
  cintura_cm?: number;
  cadera_cm?: number;
};

export type NutritionTarget = {
  kcal_objetivo: number;
  proteina_g: number;
  carbohidratos_g: number;
  grasa_g: number;
  fase_aplicada: string;
  deficit_pausado_por_guardrail: boolean;
};

export type ManualReadinessInput = {
  target_date: string;
  hrv_today: number;
  hrv_baseline_28d: number;
  hrv_trend_7d: number;
  body_battery_am: number;
  training_readiness: "high" | "moderate" | "low" | "very_low" | null;
  sleep_score: number;
  acwr: number;
  joint_pain_flag: boolean;
};

export type ReadinessResult = {
  id: number;
  fecha: string;
  resultado: "red" | "yellow" | "green";
  hrv_delta_pct: number | null;
  training_readiness: string | null;
  acwr: number | null;
};

export const SESSION_TYPES = [
  "rest",
  "active_recovery",
  "strength_heavy",
  "strength_hypertrophy",
  "endurance_intervals",
  "endurance_long",
  "martial_arts_technical",
  "martial_arts_sparring",
] as const;
export type SessionTypeValue = (typeof SESSION_TYPES)[number];

export type DailySessionInput = {
  target_date: string;
  planned_session?: SessionTypeValue;
  acwr_history?: number[];
  days_to_competition?: number;
};

export type DailySessionResult = {
  session_type: string;
  volume_pct: number;
  intensity_rpe_cap: number | null;
  narrative_text: string;
  narrative_source: "llm" | "template";
};

export const DAYS_OF_WEEK = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
export type DayOfWeek = (typeof DAYS_OF_WEEK)[number];

export type TrainingBlockInput = {
  fecha_inicio: string;
  fecha_fin: string;
  objetivo_prioritario: string;
  objetivos_mantenimiento?: string[];
  weekly_schedule?: Partial<Record<DayOfWeek, SessionTypeValue>>;
};

export type TrainingBlock = {
  id: number;
  fecha_inicio: string;
  fecha_fin: string;
  objetivo_prioritario: string;
  semana_actual: number;
  es_deload: boolean;
};

export type TrainingLoad = {
  acute_avg_7d: number | null;
  chronic_avg_28d: number | null;
  acwr: number | null;
  dias_con_dato_agudo: number;
  dias_con_dato_cronico: number;
  datos_suficientes: boolean;
};

export type ExerciseCategory = {
  id: number;
  name: string;
};

export type Exercise = {
  id: number;
  nombre: string;
  categoria: string;
  equipamiento: string[];
};

export type Ingredient = {
  id: number;
  nombre: string;
  kcal_100g: number;
  proteina_100g_g: number;
  carbohidratos_100g_g: number;
  grasa_100g_g: number;
};

export type FoodLogEntry = {
  ingredient_id: number;
  nombre: string;
  amount_grams: number;
  kcal: number;
  proteina_g: number;
  carbohidratos_g: number;
  grasa_g: number;
};

export type DailyFoodLog = {
  entradas: FoodLogEntry[];
  kcal_total: number;
  proteina_g_total: number;
  carbohidratos_g_total: number;
  grasa_g_total: number;
  entradas_omitidas: number;
};

// Catálogo cerrado - debe coincidir exactamente con `_HABITO_VALORES` en
// backend/models/schema.py (ver docstring de HabitLog para el porqué de
// un catálogo cerrado en vez de texto libre).
export const HABITOS = [
  "alcohol",
  "cafeina_tarde",
  "comida_tardia",
  "estres_alto",
  "siesta",
  "ayuno_intermitente",
  "doble_sesion",
  "viaje",
] as const;

export type Habito = (typeof HABITOS)[number];

export type HabitCorrelation = {
  habito: string;
  dias_con_habito_con_dato: number;
  dias_sin_habito_con_dato: number;
  pct_red_con_habito: number | null;
  pct_red_sin_habito: number | null;
  datos_suficientes: boolean;
};

export type GarminActivity = {
  activity_id: string;
  fecha: string;
  tipo: string;
  duracion_seg: number | null;
  distancia_m: number | null;
  hr_avg: number | null;
  hr_max: number | null;
  training_effect: number | null;
};

// Épica C/E del plan de expansión (02-roadmap/03-vision-produccion.md):
// un punto del histórico de recovery de Garmin - un punto por día,
// deduplicado ya en el backend. Todos los campos son honestos con su
// ausencia (null) - nunca asumir que un valor null es 0.
export type GarminHealthDay = {
  fecha: string;
  hrv_value: number | null;
  hrv_status: string | null;
  body_battery_am: number | null;
  training_readiness: string | null;
  sleep_score: number | null;
  stress_avg: number | null;
  resting_hr: number | null;
  vo2max: number | null;
};

export type PeriodicSummary = {
  dias_con_checkin_readiness: number;
  distribucion_readiness: { green: number; yellow: number; red: number };
  training_load: TrainingLoad;
  peso_inicio_kg: number | null;
  peso_fin_kg: number | null;
  peso_delta_kg: number | null;
  actividades_totales: number;
  duracion_actividades_total_seg: number;
};

export const api = {
  createUser: (data: UserCreateInput) =>
    request<User>("/users", { method: "POST", body: JSON.stringify(data) }),
  getUser: (id: number) => request<User>(`/users/${id}`),

  createBodyMeasurement: (userId: number, data: BodyMeasurementInput) =>
    request<BodyMeasurement>(`/users/${userId}/body-measurements`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getNutritionTarget: (userId: number, targetDate: string, factorActividad = 1.55) =>
    request<NutritionTarget>(`/users/${userId}/nutrition/daily-target`, {
      method: "POST",
      body: JSON.stringify({ target_date: targetDate, factor_actividad: factorActividad }),
    }),

  manualReadinessCheckin: (userId: number, data: ManualReadinessInput) =>
    request<ReadinessResult>(`/users/${userId}/readiness/manual-checkin`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getDailySession: (userId: number, data: DailySessionInput) =>
    request<DailySessionResult>(`/users/${userId}/session/daily`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  createTrainingBlock: (userId: number, data: TrainingBlockInput) =>
    request<TrainingBlock>(`/users/${userId}/training-blocks`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getTrainingLoad: (userId: number, asOf = todayLocalDate()) =>
    request<TrainingLoad>(`/users/${userId}/session/training-load?as_of=${asOf}`),

  getExerciseCategories: () => request<ExerciseCategory[]>("/exercises/categories"),

  searchExercises: (categoryId: number, language = 2, limit = 50) =>
    request<Exercise[]>(
      `/exercises/search?category_id=${categoryId}&language=${language}&limit=${limit}`
    ),

  saveWgerToken: (userId: number, token: string) =>
    request<void>(`/users/${userId}/nutrition/wger-token`, {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  searchIngredients: (userId: number, query: string, language = 2, limit = 20) =>
    request<Ingredient[]>(
      `/users/${userId}/nutrition/ingredients/search?query=${encodeURIComponent(query)}&language=${language}&limit=${limit}`
    ),

  createFoodLogEntry: (userId: number, ingredientId: number, amountGrams: number) =>
    request<void>(`/users/${userId}/nutrition/food-log`, {
      method: "POST",
      body: JSON.stringify({ ingredient_id: ingredientId, amount_grams: amountGrams }),
    }),

  getFoodLog: (userId: number, targetDate = todayLocalDate()) =>
    request<DailyFoodLog>(`/users/${userId}/nutrition/food-log?date=${targetDate}`),

  getBodyMeasurementHistory: (userId: number, days = 90) =>
    request<BodyMeasurement[]>(
      `/users/${userId}/body-measurements/history?days=${days}`
    ),

  getReadinessHistory: (userId: number, days = 30) =>
    request<ReadinessResult[]>(`/users/${userId}/readiness/history?days=${days}`),

  setHabits: (userId: number, habitos: Habito[], targetDate = todayLocalDate()) =>
    request<void>(`/users/${userId}/habits?date=${targetDate}`, {
      method: "POST",
      body: JSON.stringify({ habitos }),
    }),

  getHabitCorrelation: (userId: number, habito: Habito, asOf = todayLocalDate()) =>
    request<HabitCorrelation>(
      `/users/${userId}/habits/correlation?habito=${habito}&as_of=${asOf}`
    ),

  getGarminActivities: (userId: number, days = 90, asOf = todayLocalDate()) =>
    request<GarminActivity[]>(
      `/users/${userId}/garmin/activities?days=${days}&as_of=${asOf}`
    ),

  getGarminHealthHistory: (userId: number, days = 90) =>
    request<GarminHealthDay[]>(`/users/${userId}/garmin/health-history?days=${days}`),

  getPeriodicSummary: (userId: number, days = 7, asOf = todayLocalDate()) =>
    request<PeriodicSummary>(
      `/users/${userId}/summary?days=${days}&as_of=${asOf}`
    ),
};
