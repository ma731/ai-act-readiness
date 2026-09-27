# Resumen ejecutivo: Cierzo Seguros ante el Reglamento de IA

*Cierzo Seguros es una aseguradora ficticia. Todo lo demás es real: la normativa a 27 de
septiembre de 2026 (con el Ómnibus Digital ya en vigor), la Encuesta Europea de Salud en
España 2020 del INE y las tarifas oficiales de Osakidetza para 2024. No es asesoramiento
jurídico.*

## Qué hay

Seis sistemas de IA. Dos son de **alto riesgo** (tarificación de salud y suscripción de
vida, anexo III 5(c)), uno es de **transparencia** (el chatbot), dos son de **riesgo
mínimo** (fraude en siniestros y tarificación de hogar) y uno, todavía en fase de compra,
incluye un **uso prohibido**.

## Qué urge

1. **No comprar Voz Calidad tal como está.** Inferir emociones de los agentes del contact
   center a partir de su voz está prohibido desde el 2 de febrero de 2025 (art. 5(1)(f)).
2. **El chatbot debe decir que es una IA.** "Luz" no se identifica como IA en ningún
   momento, y el art. 50(1) se aplica desde el 2 de agosto de 2026. Es la única obligación
   ya vencida.
3. **Marcar los textos generados** por el chatbot antes del 2 de diciembre de 2026
   (art. 50(2)).

## Cómo se ha evaluado el modelo de salud

Con datos españoles oficiales: 14.336 adultos de 18 a 64 años de la encuesta del INE, con
las mismas preguntas que un cuestionario de salud (diagnósticos, salud percibida, tabaco,
peso, comunidad autónoma) y la asistencia sanitaria que usaron en el último año. Esa
asistencia se valora con las tarifas que Osakidetza cobra a aseguradoras y otros terceros,
comprobadas una a una contra el PDF oficial.

## Qué encontró la evaluación de impacto (art. 27)

- Las personas nacidas en el extranjero pagarían **1,17 veces** su parte del coste
  sanitario (intervalo del 95 %: 0,96 a 1,44). Es una señal que vigilar, no una infracción
  demostrada: el intervalo llega a 1. El país de nacimiento nunca es una variable del modelo.
- Además dejan de recibir atención médica por motivos económicos más a menudo:
  **2,7 %** frente al **1,8 %** de los nacidos en España. Parte de su menor uso parece
  menor acceso, no menor necesidad.
- **El sexo se cuela un poco**: sin usarlo, el modelo cotiza a las mujeres 1,17 veces lo
  que a los hombres, con un coste 1,12 veces mayor. Dentro de la tolerancia.
- **La salud percibida pesa más que cualquier diagnóstico** y sigue a la clase social: a
  igual edad, la declara regular o peor el **10,8 %** de la clase más alta y el **22,9 %**
  de los trabajadores no cualificados.
- Varias condiciones del cuestionario apenas predicen el coste. Desde la Ley 4/2018, cada
  recargo por una condición de salud necesita una justificación actuarial documentada.

## Qué recomendamos

- Medir lo mismo sobre la cartera real de Cierzo, usando el art. 10(5) para tratar datos de
  origen solo con fines de detección de sesgos.
- Tarificar la necesidad y no solo el uso pasado, y volver a medir a los nacidos fuera.
- Justificar por escrito cada recargo y el peso de la salud percibida.
- Planificar el cumplimiento de alto riesgo para el **2 de diciembre de 2027**, sin confiar
  en la exención del art. 111(2): la revisión anual de la tarifa probablemente cuenta como
  un cambio significativo de diseño.

Detalle: [clasificación](01_classification.md), [evaluación de impacto](02_fria_tarifa_salud.md),
[brechas y hoja de ruta](03_gap_assessment.md).
