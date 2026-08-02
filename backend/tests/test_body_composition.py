"""Tests para engine.body_composition — TDD.

Fórmula US Navy (ver 00-research/05-analisis-corporal-foto.md):
- Hombre: %BF = 495/(1.0324 - 0.19077*log10(cintura-cuello) + 0.15456*log10(altura)) - 450
- Mujer:  %BF = 495/(1.29579 - 0.35004*log10(cintura+cadera-cuello) + 0.22100*log10(altura)) - 450
(medidas en pulgadas; el módulo recibe cm y convierte internamente)

Principio "nunca un número falso-preciso": el resultado es SIEMPRE un
rango (± margen de incertidumbre documentado, ~3-4% MAE vs DEXA en la
literatura), nunca un único valor puntual.
"""
import math

import pytest

from engine.body_composition import BodyFatEstimate, estimate_body_fat_navy


class TestEstimateBodyFatNavyHombre:
    def test_calculo_de_referencia_hombre(self):
        # altura 177.8cm(70in), cuello 38.1cm(15in), cintura 86.36cm(34in)
        # -> BF puntual esperado ~11.05% (calculado con la fórmula US Navy)
        resultado = estimate_body_fat_navy(
            sexo="M", altura_cm=177.8, cuello_cm=38.1, cintura_cm=86.36
        )
        assert isinstance(resultado, BodyFatEstimate)
        centro = (resultado.rango_min + resultado.rango_max) / 2
        assert centro == pytest.approx(11.05, abs=0.1)

    def test_rango_min_es_menor_que_rango_max(self):
        resultado = estimate_body_fat_navy(
            sexo="M", altura_cm=177.8, cuello_cm=38.1, cintura_cm=86.36
        )
        assert resultado.rango_min < resultado.rango_max

    def test_metodo_es_navy(self):
        resultado = estimate_body_fat_navy(
            sexo="M", altura_cm=177.8, cuello_cm=38.1, cintura_cm=86.36
        )
        assert resultado.metodo == "navy"

    def test_hombre_no_requiere_cadera(self):
        # No debe lanzar aunque cadera_cm no se proporcione.
        resultado = estimate_body_fat_navy(
            sexo="M", altura_cm=177.8, cuello_cm=38.1, cintura_cm=86.36, cadera_cm=None
        )
        assert resultado.rango_min > 0

    def test_rechaza_cintura_menor_o_igual_que_cuello(self):
        # log10 de un número <= 0 no está definido - error de medición
        # probable (cinta mal colocada), debe rechazarse explícitamente.
        with pytest.raises(ValueError):
            estimate_body_fat_navy(sexo="M", altura_cm=177.8, cuello_cm=40.0, cintura_cm=38.0)


class TestEstimateBodyFatNavyMujer:
    def test_calculo_de_referencia_mujer(self):
        resultado = estimate_body_fat_navy(
            sexo="F", altura_cm=165.1, cuello_cm=33.0, cintura_cm=76.2, cadera_cm=96.5
        )
        centro = (resultado.rango_min + resultado.rango_max) / 2
        assert centro == pytest.approx(5.28, abs=0.1)

    def test_mujer_requiere_cadera(self):
        with pytest.raises(ValueError):
            estimate_body_fat_navy(sexo="F", altura_cm=165.1, cuello_cm=33.0, cintura_cm=76.2)

    def test_rechaza_cintura_mas_cadera_menor_o_igual_que_cuello(self):
        with pytest.raises(ValueError):
            estimate_body_fat_navy(
                sexo="F", altura_cm=165.1, cuello_cm=200.0, cintura_cm=76.2, cadera_cm=96.5
            )


class TestValidacionGeneral:
    def test_rechaza_sexo_invalido(self):
        with pytest.raises(ValueError):
            estimate_body_fat_navy(sexo="X", altura_cm=177.8, cuello_cm=38.1, cintura_cm=86.36)

    def test_rechaza_medidas_no_positivas(self):
        with pytest.raises(ValueError):
            estimate_body_fat_navy(sexo="M", altura_cm=0, cuello_cm=38.1, cintura_cm=86.36)
        with pytest.raises(ValueError):
            estimate_body_fat_navy(sexo="M", altura_cm=177.8, cuello_cm=-5, cintura_cm=86.36)

    def test_rechaza_medidas_no_finitas(self):
        with pytest.raises(ValueError):
            estimate_body_fat_navy(
                sexo="M", altura_cm=float("nan"), cuello_cm=38.1, cintura_cm=86.36
            )

    def test_resultado_se_acota_por_abajo_en_0(self):
        # Con cintura apenas mayor que el cuello, la fórmula produce un
        # %BF matemáticamente negativo (verificado: ~-109%) - debe
        # acotarse a 0, nunca devolver un porcentaje negativo.
        resultado = estimate_body_fat_navy(
            sexo="M", altura_cm=180.0, cuello_cm=40.0, cintura_cm=40.5
        )
        assert resultado.rango_min == 0.0
        assert 0 <= resultado.rango_max <= 100

    def test_resultado_se_acota_por_arriba_en_100(self):
        # Fórmula mujer con altura baja y cintura+cadera muy grandes
        # produce un %BF matemáticamente disparatado (~207%, verificado
        # independientemente) - debe acotarse a 100.
        resultado = estimate_body_fat_navy(
            sexo="F", altura_cm=50.0, cuello_cm=10.0, cintura_cm=300.0, cadera_cm=300.0
        )
        assert resultado.rango_max == 100.0
        assert 0 <= resultado.rango_min <= 100

    def test_mujer_resultado_se_acota_en_rango_fisico(self):
        resultado = estimate_body_fat_navy(
            sexo="F", altura_cm=180.0, cuello_cm=40.0, cintura_cm=20.0, cadera_cm=20.5
        )
        assert 0 <= resultado.rango_min <= 100
        assert 0 <= resultado.rango_max <= 100

    def test_diferencia_exactamente_cero_se_rechaza(self):
        # Borde exacto: cintura == cuello -> log10(0) indefinido.
        with pytest.raises(ValueError):
            estimate_body_fat_navy(sexo="M", altura_cm=177.8, cuello_cm=40.0, cintura_cm=40.0)

    def test_sexo_en_minuscula_se_rechaza(self):
        # Contrato explícito: solo "M"/"F" en mayúscula son válidos.
        with pytest.raises(ValueError):
            estimate_body_fat_navy(sexo="m", altura_cm=177.8, cuello_cm=38.1, cintura_cm=86.36)

    def test_acepta_bordes_exactos_de_altura_y_medidas(self):
        # Límites inclusivos: no deben lanzar.
        estimate_body_fat_navy(sexo="M", altura_cm=50.0, cuello_cm=10.0, cintura_cm=11.0)
        estimate_body_fat_navy(sexo="M", altura_cm=260.0, cuello_cm=10.0, cintura_cm=11.0)

    def test_rechaza_justo_por_debajo_del_borde_de_altura(self):
        with pytest.raises(ValueError):
            estimate_body_fat_navy(sexo="M", altura_cm=49.999, cuello_cm=38.1, cintura_cm=86.36)
