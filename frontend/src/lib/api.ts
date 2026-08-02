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
  training_readiness: "high" | "moderate" | "low" | "very_low";
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
  planned_session: SessionTypeValue;
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
};
