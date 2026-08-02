"""Tests para engine.nutrition — TDD: escritos antes que la implementación.

Fuentes de las fórmulas y umbrales de referencia:
- Mifflin-St Jeor (BMR)
- Garthe et al. 2011 (https://pubmed.ncbi.nlm.nih.gov/21558571/) -> tasa de
  pérdida de peso 0.5-0.7%/semana en fase de corte para preservar masa magra.
- Proteína 1.6-2.2 g/kg (consenso de ciencia del deporte, ver
  00-research/06-periodizacion-ciencia-deportiva.md)
"""
import pytest

from engine.nutrition import (
    WeightPhase,
    UserBiometrics,
    calculate_bmr,
    calculate_tdee,
    calculate_macros,
)


class TestCalculateBMR:
    def test_bmr_hombre_referencia(self):
        # Hombre, 30 años, 80kg, 180cm -> Mifflin-St Jeor:
        # 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
        bio = UserBiometrics(peso_kg=80, altura_cm=180, edad=30, sexo="M")
        assert calculate_bmr(bio) == pytest.approx(1780, abs=1)

    def test_bmr_mujer_referencia(self):
        # Mujer, 30 años, 65kg, 165cm ->
        # 10*65 + 6.25*165 - 5*30 - 161 = 650 + 1031.25 - 150 - 161 = 1370.25
        bio = UserBiometrics(peso_kg=65, altura_cm=165, edad=30, sexo="F")
        assert calculate_bmr(bio) == pytest.approx(1370.25, abs=1)

    def test_bmr_rechaza_peso_no_positivo(self):
        with pytest.raises(ValueError):
            UserBiometrics(peso_kg=0, altura_cm=180, edad=30, sexo="M")

    def test_bmr_rechaza_peso_fuera_de_rango_fisiologico(self):
        with pytest.raises(ValueError):
            UserBiometrics(peso_kg=500, altura_cm=180, edad=30, sexo="M")

    def test_bmr_rechaza_peso_nan_o_infinito(self):
        with pytest.raises(ValueError):
            UserBiometrics(peso_kg=float("nan"), altura_cm=180, edad=30, sexo="M")
        with pytest.raises(ValueError):
            UserBiometrics(peso_kg=float("inf"), altura_cm=180, edad=30, sexo="M")

    def test_bmr_rechaza_altura_no_positiva(self):
        with pytest.raises(ValueError):
            UserBiometrics(peso_kg=80, altura_cm=0, edad=30, sexo="M")

    def test_bmr_rechaza_edad_no_positiva(self):
        with pytest.raises(ValueError):
            UserBiometrics(peso_kg=80, altura_cm=180, edad=0, sexo="M")

    def test_bmr_rechaza_edad_fuera_de_rango(self):
        with pytest.raises(ValueError):
            UserBiometrics(peso_kg=80, altura_cm=180, edad=150, sexo="M")

    def test_bmr_rechaza_sexo_invalido(self):
        with pytest.raises(ValueError):
            UserBiometrics(peso_kg=80, altura_cm=180, edad=30, sexo="X")


class TestCalculateTDEE:
    def test_tdee_aplica_factor_actividad(self):
        bio = UserBiometrics(peso_kg=80, altura_cm=180, edad=30, sexo="M")
        bmr = calculate_bmr(bio)
        tdee = calculate_tdee(bio, factor_actividad=1.55)
        assert tdee == pytest.approx(bmr * 1.55, rel=1e-6)

    def test_tdee_rechaza_factor_actividad_fuera_de_rango(self):
        bio = UserBiometrics(peso_kg=80, altura_cm=180, edad=30, sexo="M")
        with pytest.raises(ValueError):
            calculate_tdee(bio, factor_actividad=0.9)  # por debajo de sedentario real
        with pytest.raises(ValueError):
            calculate_tdee(bio, factor_actividad=3.0)  # fuera de rango razonable

    def test_tdee_acepta_bordes_del_rango_de_actividad(self):
        bio = UserBiometrics(peso_kg=80, altura_cm=180, edad=30, sexo="M")
        bmr = calculate_bmr(bio)
        assert calculate_tdee(bio, factor_actividad=1.0) == pytest.approx(bmr)
        assert calculate_tdee(bio, factor_actividad=2.5) == pytest.approx(bmr * 2.5)

    def test_tdee_rechaza_factor_actividad_negativo(self):
        bio = UserBiometrics(peso_kg=80, altura_cm=180, edad=30, sexo="M")
        with pytest.raises(ValueError):
            calculate_tdee(bio, factor_actividad=-1.2)


class TestCalculateMacros:
    def test_mantenimiento_no_ajusta_calorias(self):
        macros = calculate_macros(
            peso_kg=80, tdee=2500, fase=WeightPhase.MAINTENANCE
        )
        assert macros.kcal_objetivo == pytest.approx(2500, abs=1)

    def test_recomp_no_ajusta_calorias(self):
        # Recomposición: calorías de mantenimiento + proteína alta
        # (Lafontant et al. 2025), no un ajuste calórico distinto.
        macros = calculate_macros(peso_kg=80, tdee=2500, fase=WeightPhase.RECOMP)
        assert macros.kcal_objetivo == pytest.approx(2500, abs=1)

    def test_corte_aplica_deficit_dentro_del_rango_seguro(self):
        # Garthe 2011: 0.5-0.7% peso/semana. A 80kg y con ~7700kcal/kg de grasa,
        # el déficit diario seguro debe mantenerse moderado, nunca "crash diet".
        macros = calculate_macros(peso_kg=80, tdee=2500, fase=WeightPhase.CUT)
        deficit_pct = (2500 - macros.kcal_objetivo) / 2500
        assert 0.10 <= deficit_pct <= 0.25  # déficit moderado, no agresivo

    def test_superavit_es_leve_no_agresivo(self):
        macros = calculate_macros(peso_kg=80, tdee=2500, fase=WeightPhase.SURPLUS)
        surplus_pct = (macros.kcal_objetivo - 2500) / 2500
        assert 0.05 <= surplus_pct <= 0.15

    def test_proteina_en_rango_cientifico_1_6_a_2_2_g_por_kg(self):
        for fase in WeightPhase:
            macros = calculate_macros(peso_kg=80, tdee=2500, fase=fase)
            proteina_g_kg = macros.proteina_g / 80
            assert 1.6 <= proteina_g_kg <= 2.2, f"fase={fase}"

    def test_corte_prioriza_proteina_alta_para_preservar_masa_magra(self):
        # En corte, la proteína por kg debe estar en el extremo alto del rango
        # (Garthe 2011 / Campbell 2020) para minimizar pérdida de masa magra.
        macros = calculate_macros(peso_kg=80, tdee=2500, fase=WeightPhase.CUT)
        proteina_g_kg = macros.proteina_g / 80
        assert proteina_g_kg >= 2.0

    def test_macros_nunca_negativos_y_kcal_cuadra(self):
        macros = calculate_macros(peso_kg=80, tdee=2500, fase=WeightPhase.CUT)
        assert macros.proteina_g >= 0
        assert macros.carbohidratos_g >= 0
        assert macros.grasa_g >= 0
        kcal_recalculadas = (
            macros.proteina_g * 4 + macros.carbohidratos_g * 4 + macros.grasa_g * 9
        )
        assert kcal_recalculadas == pytest.approx(macros.kcal_objetivo, abs=5)

    def test_rechaza_peso_no_positivo(self):
        with pytest.raises(ValueError):
            calculate_macros(peso_kg=0, tdee=2500, fase=WeightPhase.MAINTENANCE)

    def test_rechaza_tdee_no_positivo(self):
        with pytest.raises(ValueError):
            calculate_macros(peso_kg=80, tdee=0, fase=WeightPhase.MAINTENANCE)

    def test_rechaza_tdee_nan_o_infinito(self):
        with pytest.raises(ValueError):
            calculate_macros(peso_kg=80, tdee=float("nan"), fase=WeightPhase.MAINTENANCE)
        with pytest.raises(ValueError):
            calculate_macros(peso_kg=80, tdee=float("inf"), fase=WeightPhase.MAINTENANCE)

    def test_carbohidratos_se_recortan_a_cero_si_proteina_y_grasa_superan_kcal(self):
        # Peso alto + TDEE bajo: proteína (2.2g/kg) + grasa (25% kcal) puede
        # superar el total de kcal objetivo. Los carbohidratos deben quedar
        # en 0, nunca negativos, ejercitando el clamp max(...,0).
        macros = calculate_macros(peso_kg=150, tdee=1200, fase=WeightPhase.CUT)
        assert macros.carbohidratos_g == 0
