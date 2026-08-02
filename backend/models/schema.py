"""Esquema de datos de Pulse (SQLAlchemy 2.0).

Implementa el modelo descrito en docs/01-arquitectura/03-modelo-datos.md.
Motor de producción local: PostgreSQL propio (infra/docker-compose.pulse.yml,
puerto 5433) — deliberadamente SEPARADO de la base de datos interna de
wger, para no acoplar nuestro esquema a las migraciones de wger. Los
tests usan SQLite en memoria (mismo dialecto ANSI suficiente para
verificar el esquema, sin dependencia de Docker en CI).

Principios del esquema (ver doc de arquitectura):
1. Append-only para todo lo temporal: nunca se hace UPDATE sobre
   mediciones/actividades/logs — siempre INSERT con timestamp. Estas
   tablas no tienen ninguna restricción UNIQUE sobre (user_id, fecha)
   precisamente para permitir múltiples filas por día si hace falta
   re-sincronizar o corregir. Todas llevan un índice compuesto
   (user_id, fecha) porque el patrón de consulta dominante del motor de
   reglas es "dame las métricas/logs de este usuario en un rango de
   fechas" (tendencias de 7/28 días para HRV, ACWR, etc.).
2. `raw_json` en las tablas de ingesta externa (Garmin, fotos): se
   conserva el payload crudo completo para poder reprocesar si cambia la
   lógica de negocio sin volver a golpear la API externa.
3. Nunca se persiste la imagen de una foto de progreso en esta base de
   datos - solo la ruta local cifrada y los landmarks derivados
   (principio de privacidad de 00-research/05-analisis-corporal-foto.md).

Nota de seguridad — datos de salud (revisar antes de cualquier despliegue
online, ej. Supabase/Vercel, mencionado como opción futura en
01-arquitectura/02-stack-tecnologico.md):
- `garmin_daily_metrics`, `garmin_activity` (HRV, HR, sueño, VO2max) y
  `progress_photo`/`body_measurements` (composición corporal) son datos
  de salud/biométricos — categoría especial de dato personal.
- `coach_conversation.mensaje` puede contener referencias a lesiones,
  peso, estado de ánimo del usuario.
- **Hoy (100% local, un solo usuario):** el riesgo se mitiga porque la
  base de datos vive en `localhost` sin exposición de red (ver
  infra/docker-compose.pulse.yml).
- **Antes de exponer esto online:** se requiere como mínimo (a) cifrado
  en tránsito (TLS, ya lo da Supabase/Vercel por defecto), (b) evaluar
  cifrado a nivel de columna o de disco para los campos listados arriba,
  y (c) revisar políticas de Row Level Security si se pasa a multiusuario.
  Esto es deuda de gobernanza pendiente, no bloqueante para uso local.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


_SEXO_VALORES = ("M", "F")
_FASE_PESO_VALORES = ("cut", "maintenance", "recomp", "surplus")
_ANGULO_FOTO_VALORES = ("frontal", "lateral", "espalda")
_METODO_BODYFAT_VALORES = ("navy", "navy_pose", "manual")
_READINESS_VALORES = ("red", "yellow", "green")
_ROL_CONVERSACION_VALORES = ("user", "coach")
_FUENTE_NUTRICION_VALORES = ("manual", "foto_ia", "barcode_off")
_COMIDA_VALORES = ("desayuno", "comida", "cena", "snack")


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    altura_cm: Mapped[float]
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    sexo: Mapped[str] = mapped_column(Enum(*_SEXO_VALORES, name="sexo_enum", create_constraint=True))
    fase_peso_actual: Mapped[str] = mapped_column(
        Enum(*_FASE_PESO_VALORES, name="fase_peso_enum", create_constraint=True), default="maintenance"
    )
    objetivos_activos: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, default=list)
    lesiones_activas: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, default=list)
    bloque_periodizacion_actual_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_block.id", use_alter=True, name="fk_user_profile_bloque"),
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GarminDailyMetrics(Base):
    """Append-only: sin UNIQUE(user_id, fecha) a propósito - permite
    múltiples sincronizaciones del mismo día sin perder histórico."""

    __tablename__ = "garmin_daily_metrics"
    __table_args__ = (Index("ix_garmin_daily_metrics_user_fecha", "user_id", "fecha"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    hrv_status: Mapped[str | None] = mapped_column(String(20), default=None)
    hrv_value: Mapped[float | None] = mapped_column(default=None)
    body_battery_am: Mapped[int | None] = mapped_column(default=None)
    training_readiness: Mapped[str | None] = mapped_column(String(20), default=None)
    sleep_score: Mapped[int | None] = mapped_column(default=None)
    vo2max: Mapped[float | None] = mapped_column(default=None)
    stress_avg: Mapped[int | None] = mapped_column(default=None)
    resting_hr: Mapped[int | None] = mapped_column(default=None)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GarminActivity(Base):
    __tablename__ = "garmin_activity"
    __table_args__ = (Index("ix_garmin_activity_user_fecha", "user_id", "fecha"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), index=True)
    activity_id: Mapped[str] = mapped_column(String(50))
    fecha: Mapped[date] = mapped_column(Date, index=True)
    tipo: Mapped[str] = mapped_column(String(50))
    duracion_seg: Mapped[int | None] = mapped_column(default=None)
    distancia_m: Mapped[float | None] = mapped_column(default=None)
    hr_avg: Mapped[int | None] = mapped_column(default=None)
    hr_max: Mapped[int | None] = mapped_column(default=None)
    training_effect: Mapped[float | None] = mapped_column(default=None)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BodyMeasurements(Base):
    """Append-only. `bodyfat_pct_rango_min/max` en vez de un único
    número: nunca se muestra una precisión falsa al usuario (ver
    00-research/05-analisis-corporal-foto.md)."""

    __tablename__ = "body_measurements"
    __table_args__ = (Index("ix_body_measurements_user_fecha", "user_id", "fecha"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    peso_kg: Mapped[float]
    cuello_cm: Mapped[float | None] = mapped_column(default=None)
    cintura_cm: Mapped[float | None] = mapped_column(default=None)
    cadera_cm: Mapped[float | None] = mapped_column(default=None)
    bodyfat_pct_rango_min: Mapped[float | None] = mapped_column(default=None)
    bodyfat_pct_rango_max: Mapped[float | None] = mapped_column(default=None)
    metodo: Mapped[str] = mapped_column(
        Enum(*_METODO_BODYFAT_VALORES, name="metodo_bodyfat_enum", create_constraint=True), default="manual"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProgressPhoto(Base):
    """Nunca almacena la imagen en sí, solo la ruta cifrada local y los
    landmarks derivados por MediaPipe (privacidad por diseño)."""

    __tablename__ = "progress_photo"
    __table_args__ = (Index("ix_progress_photo_user_fecha", "user_id", "fecha"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    angulo: Mapped[str] = mapped_column(Enum(*_ANGULO_FOTO_VALORES, name="angulo_foto_enum", create_constraint=True))
    ruta_cifrada_local: Mapped[str] = mapped_column(String(500))
    landmarks_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TrainingBlock(Base):
    __tablename__ = "training_block"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), index=True)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    objetivo_prioritario: Mapped[str] = mapped_column(String(50))
    objetivos_mantenimiento: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    semana_actual: Mapped[int] = mapped_column(default=1)
    es_deload: Mapped[bool] = mapped_column(Boolean, default=False)


_DIA_SEMANA_VALORES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_SESSION_TYPE_VALORES = (
    "rest",
    "active_recovery",
    "strength_heavy",
    "strength_hypertrophy",
    "endurance_intervals",
    "endurance_long",
    "martial_arts_technical",
    "martial_arts_sparring",
)


class WeeklySchedule(Base):
    """Plan semanal: qué SessionType toca cada día de la semana para un
    TrainingBlock activo. Es la pieza que permite decidir
    `planned_session` automáticamente en vez de recibirlo como parámetro
    manual en cada llamada a session_service.compute_daily_session (ver
    docs/02-roadmap/02-plan-autonomo.md, Fase F).

    Una fila por (training_block_id, dia_semana) - no append-only, a
    diferencia de los logs: el plan semanal SÍ se edita/actualiza en
    sitio si el usuario cambia el plan de un bloque activo (no es un
    historial de eventos, es configuración).
    """

    __tablename__ = "weekly_schedule"
    __table_args__ = (
        Index("ix_weekly_schedule_block_dia", "training_block_id", "dia_semana", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_block_id: Mapped[int] = mapped_column(
        ForeignKey("training_block.id"), index=True
    )
    dia_semana: Mapped[str] = mapped_column(
        Enum(*_DIA_SEMANA_VALORES, name="dia_semana_enum", create_constraint=True)
    )
    session_type: Mapped[str] = mapped_column(
        Enum(*_SESSION_TYPE_VALORES, name="session_type_schedule_enum", create_constraint=True)
    )


class ReadinessLog(Base):
    """Append-only: una fila por día con el resultado completo del
    semáforo de engine.periodization, para auditoría histórica."""

    __tablename__ = "readiness_log"
    __table_args__ = (Index("ix_readiness_log_user_fecha", "user_id", "fecha"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    hrv_delta_pct: Mapped[float | None] = mapped_column(default=None)
    training_readiness: Mapped[str | None] = mapped_column(String(20), default=None)
    body_battery_am: Mapped[int | None] = mapped_column(default=None)
    acwr: Mapped[float | None] = mapped_column(default=None)
    sleep_score: Mapped[int | None] = mapped_column(default=None)
    joint_pain_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    resultado: Mapped[str] = mapped_column(Enum(*_READINESS_VALORES, name="readiness_enum", create_constraint=True))
    sesion_recomendada: Mapped[str | None] = mapped_column(String(50), default=None)
    volumen_pct_ajustado: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NutritionLog(Base):
    __tablename__ = "nutrition_log"
    __table_args__ = (Index("ix_nutrition_log_user_fecha", "user_id", "fecha"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    comida: Mapped[str] = mapped_column(Enum(*_COMIDA_VALORES, name="comida_enum", create_constraint=True))
    fuente: Mapped[str] = mapped_column(
        Enum(*_FUENTE_NUTRICION_VALORES, name="fuente_nutricion_enum", create_constraint=True)
    )
    alimentos: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, default=list)
    kcal_estimadas: Mapped[float | None] = mapped_column(default=None)
    proteina_g: Mapped[float | None] = mapped_column(default=None)
    carbohidratos_g: Mapped[float | None] = mapped_column(default=None)
    grasa_g: Mapped[float | None] = mapped_column(default=None)
    confirmado_por_usuario: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CoachConversation(Base):
    __tablename__ = "coach_conversation"
    __table_args__ = (Index("ix_coach_conversation_user_thread", "user_id", "thread_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), index=True)
    thread_id: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(Enum(*_ROL_CONVERSACION_VALORES, name="rol_enum", create_constraint=True))
    mensaje: Mapped[str] = mapped_column(Text)
    decision_tipada_asociada: Mapped[str | None] = mapped_column(String(200), default=None)
    modelo_usado: Mapped[str | None] = mapped_column(String(50), default=None)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLog(Base):
    """Trazabilidad completa del motor de reglas (Capa 1): qué regla se
    disparó, con qué inputs, y qué decisión final se tomó. Es lo que
    permite auditar cualquier recomendación (ver 00-research/
    07-arquitectura-coach-ia.md, principio "si no se puede auditar, no
    se puede confiar")."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_modulo_timestamp", "modulo", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id"), index=True)
    modulo: Mapped[str] = mapped_column(String(50))
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    regla_disparada: Mapped[str] = mapped_column(String(100))
    output: Mapped[str] = mapped_column(String(100))
    decision_final: Mapped[str] = mapped_column(String(200))
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
