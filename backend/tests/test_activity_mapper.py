"""Tests para garmin_sync.activity_mapper — TDD.

Nombres de campo verificados contra el código fuente real de
python-garminconnect (`garminconnect/typed.py`, clase `Activity`,
clonado en recursos/repos/python-garminconnect/), no inventados: la API
cruda usa camelCase (`activityId`, `activityType.typeKey`, `duration`
en segundos, `distance` en metros, `averageHR`, `maxHR`,
`aerobicTrainingEffect`, `totalSets`/`totalReps`/`totalVolume` para
fuerza).
"""
from datetime import date

import pytest

from garmin_sync.activity_mapper import InvalidActivityError, map_raw_activity


class TestMapRawActivity:
    def test_mapea_una_actividad_de_carrera(self):
        raw = {
            "activityId": 12345,
            "startTimeLocal": "2026-08-01 07:30:00",
            "activityType": {"typeKey": "running"},
            "duration": 1800.0,
            "distance": 5000.0,
            "averageHR": 150.0,
            "maxHR": 172.0,
            "aerobicTrainingEffect": 3.2,
        }
        resultado = map_raw_activity(raw)

        assert resultado["activity_id"] == "12345"
        assert resultado["fecha"] == date(2026, 8, 1)
        assert resultado["tipo"] == "running"
        assert resultado["duracion_seg"] == 1800
        assert resultado["distancia_m"] == 5000.0
        assert resultado["hr_avg"] == 150
        assert resultado["hr_max"] == 172
        assert resultado["training_effect"] == 3.2
        assert resultado["raw_json"] == raw

    def test_mapea_una_actividad_de_fuerza_sin_distancia_ni_velocidad(self):
        # Fuerza no trae distancia/velocidad útiles (ver
        # 02-roadmap/03-vision-produccion.md, punto 2 de investigación) -
        # deben quedar en None, nunca en 0 (unknown is not zero).
        raw = {
            "activityId": 999,
            "startTimeLocal": "2026-08-02 18:00:00",
            "activityType": {"typeKey": "strength_training"},
            "duration": 2700.0,
            "averageHR": 110.0,
            "maxHR": 140.0,
        }
        resultado = map_raw_activity(raw)

        assert resultado["tipo"] == "strength_training"
        assert resultado["distancia_m"] is None

    def test_campos_ausentes_quedan_en_none_no_en_cero(self):
        raw = {
            "activityId": 1,
            "startTimeLocal": "2026-08-01 07:00:00",
            "activityType": {"typeKey": "cycling"},
        }
        resultado = map_raw_activity(raw)

        assert resultado["duracion_seg"] is None
        assert resultado["distancia_m"] is None
        assert resultado["hr_avg"] is None
        assert resultado["hr_max"] is None
        assert resultado["training_effect"] is None

    def test_sin_activity_id_lanza_invalid_activity_error(self):
        with pytest.raises(InvalidActivityError):
            map_raw_activity({"startTimeLocal": "2026-08-01 07:00:00"})

    def test_sin_fecha_lanza_invalid_activity_error(self):
        with pytest.raises(InvalidActivityError):
            map_raw_activity({"activityId": 1})

    def test_sin_activity_type_usa_tipo_desconocido_en_vez_de_lanzar(self):
        # activityType puede faltar en payloads corruptos/parciales de la
        # API real - no es motivo para descartar la actividad entera
        # (tiene fecha/duración/HR útiles), pero tampoco se debe inventar
        # un deporte - se marca explícitamente como "desconocido".
        raw = {
            "activityId": 5,
            "startTimeLocal": "2026-08-01 07:00:00",
            "duration": 600.0,
        }
        resultado = map_raw_activity(raw)
        assert resultado["tipo"] == "desconocido"

    def test_redondea_en_vez_de_truncar_duracion_y_frecuencia_cardiaca(self):
        # MEDIUM de code-review: Garmin entrega duration/averageHR/maxHR
        # como float - truncar con int() sesga sistemáticamente hacia
        # abajo (1799.87 -> 1799), round() es lo semánticamente correcto.
        raw = {
            "activityId": 7,
            "startTimeLocal": "2026-08-01 07:00:00",
            "duration": 1799.87,
            "averageHR": 150.6,
            "maxHR": 172.4,
        }
        resultado = map_raw_activity(raw)
        assert resultado["duracion_seg"] == 1800
        assert resultado["hr_avg"] == 151
        assert resultado["hr_max"] == 172

    def test_starttimelocal_con_formato_inesperado_lanza_invalid_activity_error(self):
        # LOW de code-review: sin este fix, un ValueError crudo de
        # strptime escaparía de sync_activities (que solo captura
        # InvalidActivityError) y tumbaría el lote entero.
        with pytest.raises(InvalidActivityError):
            map_raw_activity({"activityId": 8, "startTimeLocal": "no-es-una-fecha"})
