from garmin_sync.exercise_set_mapper import map_raw_exercise_set


class TestMapRawExerciseSet:
    def test_mapea_los_campos_normales_de_una_serie_activa(self):
        raw = {
            "setType": "ACTIVE",
            "repetitionCount": 10,
            "weight": 60000,
            "category": "BENCH_PRESS",
            "duration": 45.3,
        }
        resultado = map_raw_exercise_set(raw, numero_serie=0)
        assert resultado["numero_serie"] == 0
        assert resultado["tipo_serie"] == "ACTIVE"
        assert resultado["repeticiones"] == 10
        assert resultado["peso_kg"] == 60.0
        assert resultado["categoria_ejercicio"] == "BENCH_PRESS"
        assert resultado["duracion_seg"] == 45
        assert resultado["raw_json"] == raw

    def test_serie_de_descanso_sin_peso_ni_repeticiones_queda_none(self):
        raw = {"setType": "REST", "duration": 60}
        resultado = map_raw_exercise_set(raw, numero_serie=1)
        assert resultado["tipo_serie"] == "REST"
        assert resultado["repeticiones"] is None
        assert resultado["peso_kg"] is None
        assert resultado["categoria_ejercicio"] is None
        assert resultado["duracion_seg"] == 60

    def test_categoria_ausente_usa_el_primer_ejercicio_detectado_como_respaldo(self):
        raw = {
            "setType": "ACTIVE",
            "repetitionCount": 8,
            "exercises": [{"category": "SQUAT", "probability": 0.9}],
        }
        resultado = map_raw_exercise_set(raw, numero_serie=2)
        assert resultado["categoria_ejercicio"] == "SQUAT"

    def test_peso_cero_real_no_se_confunde_con_ausente(self):
        raw = {"setType": "ACTIVE", "repetitionCount": 15, "weight": 0}
        resultado = map_raw_exercise_set(raw, numero_serie=3)
        assert resultado["peso_kg"] == 0.0
