# Análisis de composición corporal por foto

## Precisión real (evidencia científica, no marketing)

| Estudio | N | Resultado |
|---|---|---|
| Majmudar et al. 2022, npj Digital Medicine ([nature.com](https://www.nature.com/articles/s41746-022-00628-3)) | 134 | Método VBC (Amazon Halo, 2 fotos front+back): MAE 2.16%±1.54% vs DEXA — mejor que BIA de consumo/profesional |
| Estudio brasileño 2025 ([PMC11743147](https://pmc.ncbi.nlm.nih.gov/articles/PMC11743147/)) | 1273 | AI-2D-foto vs DEXA: CCC≥0.96, mejor que InBody/Omron (CCC 0.90-0.92) |

**Importante:** ambos estudios se hicieron en laboratorio controlado (iluminación fija, poses estandarizadas). En uso doméstico real, apps comerciales serias reconocen **±3-5% de error**, similar a lo que logra un entrenador haciendo evaluación visual.

## Métodos comparados para self-tracking casero

| Método | Precisión típica | Para este proyecto |
|---|---|---|
| Fórmula Navy (cinta: cuello/cintura/cadera) | MAE ~3-4% | ✅ Base auditable, sin caja negra, gratis |
| Foto 2D + MediaPipe Pose → medidas → fórmula | Similar o algo peor que medir a mano (problema de escala/profundidad sin referencia) | ✅ Automatiza la medición, on-device, gratis |
| CNN sobre silueta (estilo VBC, MAE 2%) | Mejor precisión publicada | ❌ Modelo propietario no disponible; requeriría dataset DEXA propio para entrenar |
| SMPL-X / PARE (3D paramétrico) | Sin validación clínica directa de %grasa | ❌ Licencias de investigación no comercial (Max Planck); solo útil para visualización estética 3D, no como medida |

## Modelos descargables disponibles

- **[ChanMeng666/bodyfat-estimation-mlp](https://huggingface.co/ChanMeng666/bodyfat-estimation-mlp)** (Apache-2.0) — MLP sobre medidas antropométricas, R²=0.97. Opera sobre números, no sobre imagen directa.
- **[frankbigshuai/BodyFatEstimator](https://github.com/frankbigshuai/BodyFatEstimator)** (MIT) — ResNet-50+U2Net, pesos incluidos, entrenado en fotos "shirtless" (calidad de dataset limitada).
- **MediaPipe Pose (BlazePose, Google, Apache-2.0)** — gratis, on-device, 33 landmarks 3D + segmentación de silueta. La pieza más sólida y reutilizable del stack.

## Cómo comunican la incertidumbre las apps serias

- **LeanLens**: siempre da un **rango**, nunca un número puntual. Cita: *"Ranges are more honest for photo-based inputs."* No almacena las fotos.
- **BiteKit**: declara explícitamente **±3-5% margin of error**. Protocolo: ropa ajustada/mínima, luz uniforme, misma hora del día.
- **GainFrame**: recomienda ventanas de **4-6 semanas** para evaluar tendencia, nunca reaccionar a una sola foto.

## Recomendación técnica para Pulse

**Arquitectura: 100% on-device, dos etapas**

1. **Extracción de geometría**: MediaPipe Pose (`enable_segmentation=True`) sobre 2-3 fotos fijas (frontal + lateral, opcional espalda).
2. **Estimación numérica**:
   - Vía primaria: fórmula Navy calculada con medidas derivadas de landmarks calibrados con la altura conocida del usuario (input manual).
   - Vía secundaria opcional: capa de regresión ligera (tipo MLP de ChanMeng666, entrenable localmente) que afine con ratios de silueta.
3. **No usar SMPL-X/PARE** — coste de licencia/cómputo no justificado para uso personal.
4. **No intentar replicar VBC** sin dataset DEXA propio — cualquier CNN entrenada sin ese dataset generalizará peor que Navy calibrado.

**Cómo mostrar el resultado:**
- Siempre un rango (ej. "18-21% ±3%"), nunca un número puntual.
- Gráfica de tendencia de 4-6 semanas con banda de incertidumbre, priorizada sobre la lectura del día.
- Etiquetar el método usado ("estimado con fórmula Navy + IA de silueta, no equivalente a DEXA").
- Protocolo de foto recordado en la UI: misma hora (mañana en ayunas), misma distancia/altura de cámara, luz difusa uniforme, ropa mínima consistente, pose relajada.

**Privacidad:**
- Pipeline de MediaPipe corre en el dispositivo — cero fotos salen del móvil para el cálculo.
- Fotos de progreso en almacenamiento cifrado propio de la app (no galería del sistema), con borrado total disponible.
