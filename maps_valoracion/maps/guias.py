"""Ayuda de cada especialista: icono, descripción corta (tooltip) y guía metodológica que recibe en su prompt."""

AYUDA: dict[str, dict] = {
    "encargo": {
        "icono": ":material/explore:",
        "resumen": "Fija las reglas del juego: qué se valora, para qué, con qué métodos y qué datos hay y faltan.",
        "guia": """1. Estándar de valor según el propósito: inversión en bolsa → valor intrínseco frente a precio; venta/compra → valor de mercado (rango negociable) y valor de inversión con sinergias para el comprador; fiscal/herencia → valor razonable defendible; fairness opinion → valor razonable con métodos múltiples.
2. Perímetro: 100 % del equity, participación mayoritaria (prima de control) o minoritaria (descuento por falta de control 10-25 % y por iliquidez si no cotiza).
3. Métodos según el tipo de empresa:
   - Empresa madura con caja estable: DCF (principal) + comparables + transacciones.
   - Crecimiento/startup: DCF con escenarios + múltiplos de ventas.
   - Holding o varias divisiones: suma de partes.
   - Intensiva en activos o en pérdidas: NAV como suelo.
   - Banco/aseguradora: DDM con exceso de capital + P/VC tangible justificado + comparables; nunca FCFF ni WACC.
4. Inventario de datos: tabla «dato necesario · disponible (sí/no/parcial) · fuente». Da prioridad a los datos aportados (documentos, Yahoo Finance) frente al conocimiento general.
5. Top 5 riesgos para el valor, concretos para esta empresa.
Errores típicos: elegir métodos sin justificar; no fijar la fecha de valoración; mezclar valor de empresa y valor del equity.""",
    },
    "financiero": {
        "icono": ":material/receipt_long:",
        "resumen": "Limpia y ordena las cuentas históricas para saber cuánto gana y cuánta caja genera de verdad la empresa.",
        "guia": """1. Tabla de 3-5 años: ventas, crecimiento, margen bruto, EBITDA, EBIT, beneficio neto, capex, variación de circulante, flujo de caja libre.
2. Normalizaciones (una fila por ajuste, con importe y motivo): resultados no recurrentes (ventas de activos, deterioros, indemnizaciones, litigios), sueldos de socios fuera de mercado, alquileres a vinculadas, subvenciones puntuales. EBITDA ajustado = EBITDA contable ± ajustes.
3. IFRS 16: indica si el EBITDA incluye el alquiler o no. Si la deuda neta incluye arrendamientos, el EBITDA debe ser post-IFRS 16 (sin alquiler); sé coherente de principio a fin.
4. Circulante (NOF) = existencias + clientes − proveedores. Días de cobro = clientes / ventas × 365; días de pago = proveedores / compras × 365; días de existencias = existencias / coste de ventas × 365.
5. Deuda financiera neta = deuda bancaria + bonos + arrendamientos (si procede) − caja e inversiones líquidas. Asimilables a deuda: provisiones por pensiones, dividendos pendientes, pagos aplazados de adquisiciones, litigios probables. Minoritarios y participaciones en asociadas van aparte en el puente EV → equity.
6. Conversión a caja = FCF / EBITDA. Si es inferior al 40-50 %, explica por qué (capex, circulante).
7. Capex de mantenimiento ≈ amortización (orientativo); el exceso es capex de crecimiento.
Errores típicos: sumar mal los ajustes; restar dos veces los arrendamientos; confundir años fiscales (p. ej. un ejercicio que cierra en enero).""",
    },
    "sector": {
        "icono": ":material/factory:",
        "resumen": "Estudia el mercado y la competencia para saber cuánto puede crecer la empresa y qué riesgo tiene.",
        "guia": """1. Mercado: tamaño, crecimiento histórico y esperado (nominal), ciclicidad y factores de demanda.
2. Cinco fuerzas de Porter en una tabla (fuerza · intensidad baja/media/alta · por qué).
3. Ventajas competitivas (marca, costes, red, cambio de proveedor costoso, regulación) y cuánto pueden durar.
4. Posición de la empresa: cuota, crecimiento frente al mercado y márgenes frente a los competidores.
5. Concentración: % de ventas de los 5 principales clientes y dependencia de proveedores.
6. Traducción cuantitativa obligatoria:
   - Crecimiento sostenible de ventas a 5 años (rango).
   - Margen EBITDA sostenible (rango).
   - Prima de riesgo específica sugerida (0-5 pp) y su motivo.
Errores típicos: análisis genérico que valdría para cualquier empresa; no convertir las conclusiones en números.""",
    },
    "proyecciones": {
        "icono": ":material/trending_up:",
        "resumen": "Proyecta ventas, beneficios y caja de los próximos 5 años en tres escenarios.",
        "guia": """1. Horizonte de 5 años más un año normalizado (año terminal). Tres escenarios: base, optimista y pesimista, cada uno con su supuesto de crecimiento y margen.
2. FCFF = EBIT × (1 − t) + amortizaciones − capex − ΔNOF. Tipo impositivo: el legal del país (España 25 %) salvo que haya motivos para otro, como bases imponibles negativas.
3. Coherencia:
   - Crecimiento alto → capex por encima de la amortización.
   - NOF proporcional a las ventas (usa los días históricos).
   - En el año terminal, capex ≈ amortización × (1 + g).
4. Crecimiento a largo plazo g: 1,5-2,5 % en zona euro, nunca por encima del crecimiento nominal del PIB a largo plazo.
5. Márgenes: converge hacia el margen sostenible del analista sectorial; no extrapoles un año excepcional.
6. Si hay consenso de analistas (Yahoo u otra fuente), contrasta con él tu escenario base y explica la diferencia.
Errores típicos: palo de hockey sin justificar; olvidar la variación de circulante; amortización mayor que el capex a perpetuidad.""",
    },
    "wacc": {
        "icono": ":material/percent:",
        "resumen": "Calcula la rentabilidad mínima que exigen accionistas y bancos: la tasa para descontar los flujos futuros.",
        "guia": """1. Ke (CAPM ampliado) = Rf + βL × PRM + prima de tamaño + prima específica (+ prima país si aplica).
   - Rf: bono a 10 años del país de la moneda de los flujos (usa el dato aportado; si no lo hay, márcalo [SUPUESTO]).
   - PRM: 5-6,5 % habitual.
   - Prima de tamaño: 0-1 pp en grandes cotizadas y 2-5 pp en pymes.
2. Beta: desapalanca la de los comparables con βU = βL / (1 + (1 − t) × D/E), toma la mediana y reapalanca a la estructura objetivo. La beta de Yahoo (5 años, mensual) es solo una referencia.
3. Kd = Rf + diferencial de crédito (ratings BBB ~1-2 %; pymes 2-4 %), o el coste medio real de la deuda. Kd después de impuestos = Kd × (1 − t).
4. Estructura objetivo D/(D+E): la del sector o la de los comparables, no necesariamente la actual.
5. WACC = E/(D+E) × Ke + D/(D+E) × Kd × (1 − t). Da un rango de ±0,5-1 pp y un valor central.
Contraste: grandes cotizadas europeas WACC 6-9 %; pymes 9-14 %. Si te sales de ahí, justifícalo.
Errores típicos: usar la beta apalancada de otra empresa sin reapalancar; mezclar moneda del bono y de los flujos; restar dos veces el riesgo específico.""",
    },
    "dcf": {
        "icono": ":material/calculate:",
        "resumen": "Calcula el valor descontando al día de hoy la caja que generará la empresa.",
        "guia": """1. Descuenta el FCFF del escenario base con el factor 1/(1 + WACC)^t. Usa convención de mitad de año (t − 0,5) si los flujos llegan a lo largo del año y dilo. Muestra la tabla año · FCFF · factor · valor actual.
2. Valor terminal por Gordon: VT = FCFF(n+1) / (WACC − g), descontado con el factor del año n.
3. Contraste con múltiplo de salida: VT / EBITDA(n+1) debe ser razonable frente a los comparables. Si difiere mucho, explica por qué.
4. Peso del VT en el EV: normalmente 60-80 %. Por encima del 85 %, advierte de que el valor depende casi todo de la perpetuidad.
5. Puente EV → equity: EV − deuda financiera neta − asimilables a deuda − minoritarios + activos no operativos (asociadas, excesos de caja, inmuebles no afectos). Debe coincidir con la deuda neta del analista financiero.
6. Valor por acción = equity / acciones diluidas.
7. Resume en una línea los escenarios optimista y pesimista.
Errores típicos: descontar el VT con el factor del año n+1; g ≥ WACC; restar arrendamientos en el puente cuando el FCFF ya descuenta el alquiler.""",
    },
    "comps": {
        "icono": ":material/compare_arrows:",
        "resumen": "Compara con empresas parecidas que cotizan para ver a cuántas veces su beneficio se pagan.",
        "guia": """1. Selecciona 4-8 comparables del mismo negocio, modelo y geografía, con una línea que justifique cada uno. Si hay datos de Yahoo Finance en la información, úsalos y cítalos.
2. Tabla: EV/EBITDA, EV/EBIT, EV/Ventas, PER (y P/VC tangible en bancos), del año actual y del siguiente si los hay. Da la mediana y el rango intercuartílico (descarta extremos, sin usar la media simple).
3. Ajusta el múltiplo de la empresa frente a la mediana:
   - Tamaño: pymes con un descuento del 20-40 % frente a cotizadas grandes.
   - Crecimiento y rentabilidad: prima o descuento razonado.
   - Iliquidez: descuento del 15-30 % si no cotiza.
4. Aplica los múltiplos a la métrica normalizada del analista financiero. EV → equity con el mismo puente que el DCF.
5. Resultado: rango de valor del equity con cada cálculo visible.
Errores típicos: aplicar múltiplos de EV a beneficio neto; mezclar EBITDA pre y post IFRS 16; comparables de otro sector.""",
    },
    "mercado": {
        "icono": ":material/candlestick_chart:",
        "resumen": "Mira qué dice la bolsa: cuánto vale hoy la acción y qué expectativas descuenta el precio.",
        "guia": """1. Datos de mercado: precio, acciones, capitalización, EV, rango de 52 semanas, liquidez, free float (con fecha y fuente, preferiblemente Yahoo Finance si se ha aportado).
2. Múltiplos implícitos al precio actual frente a la mediana de los comparables.
3. Valoración inversa: con el WACC de la cadena, ¿qué crecimiento o margen a perpetuidad justifica el precio actual? Despeja g o el margen y compáralo con las proyecciones.
4. Consenso de analistas: precio objetivo medio, rango y recomendación. Diferencia frente al valor de la cadena.
5. Explica la diferencia precio-valor: expectativas del mercado, riesgos que la cadena no recoge o posibles errores de la cadena.
6. Si no cotiza: valor estimado como cotizada y descuento por iliquidez aplicable (15-30 %).
Errores típicos: comparar valor del equity con EV; usar precios de fechas distintas sin decirlo.""",
    },
    "precedentes": {
        "icono": ":material/handshake:",
        "resumen": "Busca compras de empresas parecidas para ver cuánto se pagó por ellas.",
        "guia": """1. Transacciones de los últimos 5-7 años del mismo sector: fecha, comprador, objetivo, EV, EV/EBITDA, EV/Ventas (en bancos P/VC tangible) y tipo de comprador (estratégico o fondo).
2. Múltiplos de transacción: normalmente superiores a los cotizados porque incluyen prima de control (20-40 % sobre el precio de mercado).
3. Ajusta por momento del ciclo (tipos de interés, múltiplos del mercado de esa época) y por tamaño.
4. Rango de valor: mediana y rango aplicados al EBITDA normalizado, y paso a equity con el mismo puente que el DCF.
5. Compara con los comparables cotizados y explica la diferencia (prima de control, sinergias pagadas).
Si no tienes datos concretos, márcalos como [SUPUESTO] con órdenes de magnitud, y pide la lista en «Datos que faltan».
Errores típicos: inventar operaciones; mezclar operaciones minoritarias y de control.""",
    },
    "sinergias": {
        "icono": ":material/join_inner:",
        "resumen": "Calcula cuánto más valdría la empresa para un comprador concreto y cuánto podría llegar a pagar.",
        "guia": """1. Sinergias de costes (compras, estructura, logística): importe anual, año en que se alcanzan (habitual 2-3 años) y probabilidad (70-90 %).
2. Sinergias de ingresos (venta cruzada, precios): probabilidad menor (30-50 %).
3. Costes de integración: habitualmente 1-1,5 veces las sinergias anuales de costes, en los años 1-2.
4. Valor actual de las sinergias netas = VA(sinergias × probabilidad) − VA(costes de integración), descontado al WACC del comprador.
5. Precio máximo del comprador estratégico = valor independiente + VA de las sinergias. Reparto habitual: el vendedor captura un 30-50 %.
6. Comprador financiero: precio máximo limitado por su TIR objetivo (ver LBO).
7. Estructura: contado o acciones, earn-out ligado a EBITDA si hay mucha incertidumbre, pago aplazado, escrow del 5-15 % para contingencias.
Errores típicos: dar las sinergias por seguras; olvidar los costes de integración; contar dos veces el crecimiento ya incluido en las proyecciones.""",
    },
    "acrecion": {
        "icono": ":material/stacked_line_chart:",
        "resumen": "Comprueba si la compra sube o baja el beneficio por acción del comprador según cómo se pague.",
        "guia": """1. Datos del comprador (de la información o un comprador típico [SUPUESTO]): beneficio neto, número de acciones, BPA, PER y coste de la deuda.
2. Combinaciones: 100 % caja, 100 % deuda, 100 % acciones y una mixta.
3. BPA combinado = (BN comprador + BN objetivo + sinergias × (1 − t) − intereses nuevos × (1 − t) − rendimiento perdido de la caja × (1 − t)) / (acciones antiguas + acciones nuevas).
4. Acreción/dilución = BPA combinado / BPA comprador − 1. Da la tabla por combinación.
5. Precio umbral: el precio a partir del cual la operación diluye, por combinación. Regla rápida: con acciones, acrece si el PER del comprador es mayor que el PER pagado.
6. Apalancamiento resultante: deuda neta / EBITDA combinado. Advierte si supera 3-3,5x.
Errores típicos: olvidar el efecto fiscal de los intereses; ignorar la amortización de intangibles de la compra si es relevante.""",
    },
    "lbo": {
        "icono": ":material/account_balance:",
        "resumen": "Simula la compra por un fondo con mucha deuda para saber el precio máximo que pagaría.",
        "guia": """1. Deuda máxima: 4-6x EBITDA (según sector y estabilidad de la caja); en pymes 3-4x. Coste 6-9 % (orientativo, márcalo [SUPUESTO] si no hay datos).
2. Fuentes y usos: precio + comisiones (2-3 %) = deuda + equity del fondo.
3. Calendario de 5 años: EBITDA, intereses, impuestos, capex, ΔNOF, caja para amortizar deuda y deuda al final de cada año.
4. Salida en el año 5 al mismo múltiplo de entrada (caso base); equity de salida = EV de salida − deuda neta.
5. TIR y MOIC del fondo. Objetivo habitual: TIR del 20-25 % y MOIC de 2,5-3x.
6. Precio máximo: busca el precio de entrada que da una TIR del 20 % y muéstralo como EV y como equity.
Errores típicos: salir a un múltiplo mayor que el de entrada sin justificarlo; olvidar las comisiones; no comprobar que la deuda se puede pagar (cobertura de intereses mayor que 2x).""",
    },
    "sotp": {
        "icono": ":material/dashboard:",
        "resumen": "Valora cada negocio de la empresa por separado y suma las partes.",
        "guia": """1. Identifica los segmentos con sus ventas, EBITDA o beneficio y sus activos (de la información segmentada).
2. Método por segmento: múltiplo de comparables del segmento, DCF o NAV (inmobiliario, participaciones cotizadas a precio de mercado).
3. Costes centrales no asignados: capitalízalos con un múltiplo (resta EBITDA central × múltiplo medio).
4. Suma de EV de los segmentos − costes centrales − deuda neta del grupo − minoritarios = equity.
5. Compara con la valoración consolidada y con la capitalización: descuento de holding o conglomerado (habitual 10-30 %) y motivo.
Errores típicos: contar la deuda de filiales dos veces; aplicar múltiplos de un segmento a otro.""",
    },
    "activos": {
        "icono": ":material/domain:",
        "resumen": "Calcula cuánto valen los bienes de la empresa menos sus deudas: el valor mínimo razonable.",
        "guia": """1. Parte del balance más reciente y ajusta cada partida a valor de mercado:
   - Inmuebles: tasación o €/m² de la zona.
   - Existencias: descuento por obsolescencia.
   - Clientes: menos los dudosos.
   - Participaciones: a valor de mercado.
   - Intangibles identificables: marcas y licencias, si se pueden vender por separado.
2. NAV ajustado = activos ajustados − pasivos exigibles (incluidas contingencias).
3. Efecto fiscal de las plusvalías latentes (25 % en España) si se venderían los activos.
4. Valor de liquidación ordenada: aplica descuentos por venta rápida (inmuebles 10-20 %, existencias 30-60 %, maquinaria 50-80 %) y resta costes de cierre (indemnizaciones, asesores).
5. Conclusión: úsalo como suelo del valor y compáralo con los métodos por flujos.
Errores típicos: sumar el fondo de comercio contable como si fuera vendible; olvidar indemnizaciones laborales en la liquidación.""",
    },
    "ddm": {
        "icono": ":material/account_balance_wallet:",
        "resumen": "Valora bancos y aseguradoras por los dividendos y el capital que pueden repartir.",
        "guia": """1. Ke = Rf + β × PRM (+ prima país). En bancos europeos suele estar entre el 9 y el 12 %.
2. Proyección a 3-5 años: beneficio, ROTE, activos ponderados por riesgo (APR), CET1 y payout.
3. Exceso de capital = CET1 actual − CET1 objetivo (requisito regulatorio más colchón de gestión, a menudo 12-13 %) × APR. Repártelo como dividendo extraordinario o recompras.
4. DDM: VA de los dividendos más recompras + valor terminal = dividendo(n+1) / (Ke − g), con g de 2-3 %.
5. P/VC tangible justificado = (ROTE sostenible − g) / (Ke − g). Valor = múltiplo × VC tangible por acción.
6. Contrasta con los comparables bancarios (P/VC tangible y PER) y da el valor por acción por ambas vías.
Errores típicos: usar FCFF o WACC (nunca en bancos); ROTE sostenible igual al de un año excepcional; olvidar las AT1 al calcular el equity.""",
    },
    "due": {
        "icono": ":material/policy:",
        "resumen": "Busca los riesgos ocultos (contables, fiscales, legales…) que bajan el precio o exigen garantías.",
        "guia": """1. Revisa por áreas: contable, fiscal, laboral, legal, regulatoria, comercial, tecnológica y ESG.
   - Contable: reconocimiento de ingresos, provisiones insuficientes, capitalización agresiva de gastos.
   - Fiscal: inspecciones abiertas, bases imponibles negativas aprovechables (valor = VA del ahorro fiscal).
   - Laboral: litigios, convenios, personal clave.
   - Legal: contratos con cláusula de cambio de control, litigios, licencias.
   - Comercial: dependencia de clientes o proveedores.
   - ESG: emisiones, sanciones, reputación.
2. Tabla: riesgo · probabilidad (alta/media/baja) · impacto estimado en € · tratamiento (menor precio, escrow, garantía específica, condición previa).
3. Ordena por impacto esperado (probabilidad × importe).
4. Solo riesgos concretos de esta empresa, basados en la información. Si faltan datos, di qué habría que pedir en una due diligence real.
Errores típicos: lista genérica; no cuantificar; contar dos veces riesgos ya recogidos en las proyecciones.""",
    },
    "sensibilidad": {
        "icono": ":material/tune:",
        "resumen": "Muestra cuánto cambia el valor si cambian los supuestos clave, y el valor medio esperado.",
        "guia": """1. Identifica las 3 variables que más mueven el valor (normalmente WACC o Ke, g y margen EBITDA; en bancos ROTE y Ke).
2. Mínimo dos tablas bidimensionales de 5×5, por ejemplo WACC (±1 pp en pasos de 0,5) × g (±1 pp) y margen × crecimiento de ventas. Valor del equity en cada celda, con el caso base resaltado.
3. Escenarios: base, optimista y pesimista con probabilidades (por ejemplo 60/20/20) y valor esperado = Σ probabilidad × valor.
4. Tornado: impacto en el valor de mover cada variable ±10 % o ±1 pp, ordenado de mayor a menor.
5. Conclusión: qué variable domina y qué dato concreto reduciría más la incertidumbre.
Errores típicos: tablas que no reproducen el caso base en la celda central; probabilidades que no suman 100 %.""",
    },
    "critico": {
        "icono": ":material/gavel:",
        "resumen": "Revisa todo el trabajo anterior buscando errores, supuestos exagerados e incoherencias.",
        "guia": """1. Coherencia entre especialistas:
   - ¿El crecimiento de las proyecciones cuadra con el sector y con el capex?
   - ¿La deuda neta del DCF es la del analista financiero?
   - ¿El WACC encaja con el riesgo descrito?
   - ¿Los múltiplos aplicados usan la misma métrica (pre/post IFRS 16)?
2. Aritmética: recalcula 3-5 cifras clave (un valor actual, el valor terminal, un múltiplo, el puente EV → equity).
3. Supuestos agresivos: g alto, margen por encima de los competidores sin motivo, prima de riesgo baja para una pyme, valor terminal por encima del 85 % del EV.
4. Dobles contabilizaciones: sinergias ya incluidas en las proyecciones, riesgos restados dos veces, arrendamientos en el FCFF y en la deuda.
5. Datos: cifras sin fuente ni [SUPUESTO] y datos desactualizados.
6. Tabla: problema · especialista · impacto estimado en valor (€ o %) · corrección propuesta. Ordénala por impacto.
No rehagas la valoración: audítala. Si todo es razonable, dilo y explica qué has comprobado.""",
    },
    "sintesis": {
        "icono": ":material/flag:",
        "resumen": "Junta todos los métodos, les da un peso y llega al rango de valor final y la recomendación.",
        "guia": """1. Tabla football field: método · rango mínimo-máximo del equity · valor central · peso · motivo del peso. Todos en la misma unidad y moneda (equity, no EV).
2. Pesos orientativos:
   - Empresa madura: DCF 40-60 %, comparables 20-30 %, transacciones 10-30 %.
   - Si el propósito es una venta, más peso a las transacciones.
   - Métodos con datos poco fiables o muchos [SUPUESTO], menos peso.
   - NAV solo como suelo, salvo holdings o inmobiliarias.
3. Aplica las correcciones del abogado del diablo, indicando cuáles aceptas y cuáles no, y por qué.
4. Rango final y valor central del equity; valor por acción si hay número de acciones. Si cotiza: potencial = valor central por acción / precio − 1.
5. Resumen ejecutivo (10 líneas como máximo) y recomendación concreta según el propósito (comprar/mantener/vender; precio de salida y walk-away en una venta…).
6. Los 3-5 datos que más reducirían la incertidumbre.
Escribe las cifras del rango final de forma explícita e inequívoca (por ejemplo: «Rango final del equity: 1.200-1.450 M EUR; central 1.320 M EUR»).""",
    },
}
