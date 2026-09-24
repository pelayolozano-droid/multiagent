"""Catálogo de especialistas, presets y constantes de MAPS Valoración."""

CATALOG: list[dict] = [
    {"id": "encargo", "nombre": "Director del encargo", "grupo": "Núcleo", "fixed": True,
     "tarea": "Define el marco de la valoración: propósito y estándar de valor (valor razonable, de mercado o de inversión con sinergias), fecha, perímetro (qué se valora: 100% del equity, participación mayoritaria o minoritaria), métodos adecuados para esta empresa y por qué, e inventario de la información disponible frente a la necesaria. Señala a priori los 5 riesgos más relevantes para la valoración.",
     "criterios": ["Estándar de valor y perímetro explícitos", "Métodos elegidos y justificados según el tipo de empresa", "Inventario de datos disponibles frente a faltantes"]},
    {"id": "financiero", "nombre": "Analista de estados financieros", "grupo": "Núcleo",
     "tarea": "Reconstruye y normaliza los históricos (idealmente 3-5 años): cuenta de resultados, balance y flujos de caja. Calcula EBITDA y EBIT ajustados (no recurrentes, sueldos de socios fuera de mercado, alquileres a vinculadas…), márgenes, capital circulante (NOF) y días de cobro, pago y existencias, capex de mantenimiento frente a crecimiento, y deuda financiera neta con las partidas asimilables (provisiones, arrendamientos, dividendos pendientes). Valora la calidad del beneficio y la conversión a caja.",
     "criterios": ["Tablas de históricos con cada ajuste explicado", "Deuda neta desglosada con partidas asimilables", "Cálculos coherentes (sumas, márgenes, ratios)"]},
    {"id": "sector", "nombre": "Analista sectorial y competitivo", "grupo": "Núcleo",
     "tarea": "Analiza el sector y la posición competitiva: tamaño y crecimiento del mercado, ciclo, factores de demanda, estructura competitiva, ventajas competitivas de la empresa y su durabilidad, concentración de clientes y proveedores, regulación. Traduce el análisis en implicaciones concretas para el crecimiento, los márgenes sostenibles y la prima de riesgo específica.",
     "criterios": ["Implicaciones cuantificables para proyecciones y riesgo", "Distingue datos aportados de conocimiento general [SUPUESTO]", "Riesgos concretos, no genéricos"]},
    {"id": "proyecciones", "nombre": "Modelizador de proyecciones", "grupo": "Núcleo",
     "tarea": "Construye proyecciones a 5 años más un año normalizado para el valor terminal, en tres escenarios (base, optimista, pesimista): ventas, EBITDA, amortizaciones, EBIT, impuestos, capex, variación de NOF y flujo de caja libre operativo (FCFF). Ancla cada supuesto clave a los históricos normalizados y al análisis sectorial. Propón la tasa de crecimiento a largo plazo.",
     "criterios": ["Tabla año a año del FCFF en los tres escenarios", "Supuestos anclados a históricos y sector", "Coherencia entre capex y crecimiento, y entre NOF y ventas"]},
    {"id": "wacc", "nombre": "Especialista en coste de capital", "grupo": "Núcleo",
     "tarea": "Estima el WACC: tasa libre de riesgo, prima de riesgo de mercado, beta (desapalancada de comparables y reapalancada a la estructura objetivo), prima de tamaño y de riesgo específico, prima país si aplica, coste de la deuda antes y después de impuestos y estructura de capital objetivo. Da un rango y un valor central.",
     "criterios": ["Cada componente con valor y fuente o [SUPUESTO]", "Reapalancamiento de la beta correcto", "Rango y valor central justificados"]},
    {"id": "dcf", "nombre": "Valorador DCF", "grupo": "Núcleo",
     "tarea": "Descuenta el FCFF del escenario base al WACC (y resume el resultado de los otros dos escenarios). Calcula el valor terminal por Gordon y contrástalo con un múltiplo de salida. Haz el puente del valor de empresa (EV) al valor del equity (deuda neta, minoritarios, activos no operativos) y, si hay número de acciones, el valor por acción. Indica qué porcentaje del valor aporta el valor terminal.",
     "criterios": ["Descuento verificable (factores y valores actuales)", "Valor terminal por dos vías y contrastado", "Puente EV→equity completo y coherente con el análisis financiero"]},
    {"id": "comps", "nombre": "Analista de comparables cotizados", "grupo": "Núcleo",
     "tarea": "Selecciona un grupo de comparables cotizados razonable (justifica cada uno) y los múltiplos relevantes (EV/EBITDA, EV/EBIT, EV/Ventas, PER; en bancos P/VC tangible y PER). Si no hay cotizaciones en la información, usa órdenes de magnitud sectoriales marcados como [SUPUESTO]. Ajusta por tamaño, crecimiento, rentabilidad y liquidez (descuento por iliquidez si no cotiza) y obtén un rango de valor.",
     "criterios": ["Grupo de comparables justificado", "Ajustes explícitos de tamaño y liquidez", "Rango de valor con cálculos visibles"]},
    {"id": "mercado", "nombre": "Analista de precio de mercado", "grupo": "Mercado",
     "tarea": "Si la empresa cotiza: capitalización, valor a mercado, múltiplos implícitos frente a comparables, valoración inversa (qué crecimiento y rentabilidad descuenta el precio actual), consenso de analistas, liquidez y free float. Compara el precio con el valor intrínseco de la cadena y explica la diferencia. Si no cotiza, estima el valor que tendría en bolsa y el descuento por iliquidez aplicable.",
     "criterios": ["Valoración inversa con supuestos explícitos", "Diferencia precio–valor explicada", "Datos de mercado con fuente y fecha o [SUPUESTO]"]},
    {"id": "precedentes", "nombre": "Analista de transacciones precedentes", "grupo": "M&A",
     "tarea": "Identifica transacciones comparables del sector y los múltiplos pagados (EV/EBITDA, EV/Ventas; en bancos P/VC tangible), la prima de control implícita y el contexto (momento del ciclo, tipo de comprador). Obtén un rango de valor por transacciones y explica en qué difiere de los comparables cotizados.",
     "criterios": ["Transacciones justificadas y fechadas", "Prima de control explícita", "Rango de valor con cálculos"]},
    {"id": "sinergias", "nombre": "Especialista en M&A y sinergias", "grupo": "M&A",
     "tarea": "Valora la operación desde el lado comprador: sinergias de costes e ingresos (cuantificadas, con calendario y probabilidad), costes de integración, valor con sinergias, prima máxima justificable y reparto de sinergias entre comprador y vendedor. Distingue comprador estratégico y financiero y su precio máximo. Propón estructura: contado o acciones, earn-out, pago aplazado, garantías y escrow.",
     "criterios": ["Sinergias cuantificadas y descontadas", "Precio máximo por tipo de comprador", "Estructura de la operación concreta"]},
    {"id": "acrecion", "nombre": "Analista de acreción/dilución", "grupo": "M&A",
     "tarea": "Para el comprador indicado en la información (o uno típico del sector), calcula el impacto en el BPA y en el apalancamiento de la compra con distintas combinaciones de financiación (caja, deuda, acciones) al precio central. Indica el precio a partir del cual la operación es dilutiva.",
     "criterios": ["Tabla de acreción/dilución por combinación de financiación", "Precio umbral de dilución", "Supuestos del comprador explícitos"]},
    {"id": "lbo", "nombre": "Modelizador LBO", "grupo": "M&A",
     "tarea": "Modela una compra apalancada por un fondo: deuda máxima (múltiplo de EBITDA), fuentes y usos, calendario de amortización, salida a 5 años, TIR y MOIC del fondo. Obtén el precio máximo que pagaría un fondo para una TIR objetivo del 20-25%.",
     "criterios": ["Fuentes y usos y calendario de deuda", "TIR y MOIC calculados", "Precio máximo del fondo"]},
    {"id": "sotp", "nombre": "Suma de partes", "grupo": "Especial",
     "tarea": "Si la empresa tiene varias divisiones o activos distintos (p. ej. banca y seguros), valora cada segmento con el método y múltiplo adecuados, suma, y resta los costes centrales capitalizados y la deuda. Compara con la valoración consolidada (descuento de conglomerado).",
     "criterios": ["Segmentos valorados por separado con método justificado", "Costes centrales tratados", "Comparación con la valoración consolidada"]},
    {"id": "activos", "nombre": "Valoración por activos (NAV)", "grupo": "Especial",
     "tarea": "Calcula el valor neto de los activos ajustado a mercado (inmuebles, existencias, participaciones, intangibles identificables) y el valor de liquidación ordenada. Úsalo como suelo de valor.",
     "criterios": ["Ajustes a valor de mercado por partida", "Valor de liquidación con costes", "Conclusión como suelo de valor"]},
    {"id": "ddm", "nombre": "Dividendos / entidades financieras", "grupo": "Especial",
     "tarea": "Para bancos, aseguradoras o empresas con alto reparto: coste de los fondos propios (Ke) con tasa libre de riesgo, beta y prima de mercado; modelo de descuento de dividendos con el exceso de capital CET1 sobre el objetivo (recompras); y P/VC tangible justificado = (ROTE − g)/(Ke − g). Da valor por acción por ambas vías.",
     "criterios": ["Ke con cada componente explícito", "Exceso de capital y reparto proyectados coherentes con CET1", "P/VC tangible justificado calculado y valor por acción"]},
    {"id": "due", "nombre": "Due diligence de riesgos", "grupo": "Especial",
     "tarea": "Revisa los riesgos que ajustan el valor o el precio: contables (reconocimiento de ingresos, provisiones), fiscales (contingencias, bases imponibles negativas aprovechables), laborales, legales, regulatorios, dependencia de personas clave, clientes o proveedores, y ESG. Cuantifica cada ajuste (menor valor, garantía o escrow) cuando sea posible.",
     "criterios": ["Riesgos concretos de esta empresa", "Ajuste cuantificado o mecanismo contractual propuesto", "Prioridad por impacto"]},
    {"id": "sensibilidad", "nombre": "Sensibilidad y escenarios", "grupo": "Núcleo",
     "tarea": "Construye tablas de sensibilidad del valor del equity sobre las dos o tres variables que más lo mueven (p. ej. WACC/Ke × crecimiento a largo plazo, margen × crecimiento de ventas, ROTE × Ke en bancos). Pondera los escenarios base, optimista y pesimista con probabilidades y da el valor esperado. Identifica las 3 variables críticas.",
     "criterios": ["Al menos dos tablas de sensibilidad bidimensionales", "Valor esperado ponderado por probabilidad", "Variables críticas identificadas"]},
    {"id": "critico", "nombre": "Abogado del diablo", "grupo": "Núcleo",
     "tarea": "Audita la cadena completa: supuestos agresivos, incoherencias entre especialistas (crecimiento sin capex, tasa de descuento incoherente con el riesgo…), dobles contabilizaciones, errores de cálculo, datos desactualizados y sesgo de confirmación. Para cada problema: impacto estimado en el valor y corrección propuesta. No repitas el trabajo: audítalo.",
     "criterios": ["Problemas concretos con referencia al especialista", "Impacto en valor estimado", "Corrección propuesta para cada problema"]},
    {"id": "sintesis", "nombre": "Director de síntesis", "grupo": "Núcleo", "fixed": True,
     "tarea": "Reconcilia todos los métodos (football field): rango de cada método, pesos asignados y por qué, rango final y valor central del equity (y por acción si procede), incorporando las correcciones del abogado del diablo. Si cotiza, compara con el precio actual (potencial de revalorización). Redacta un resumen ejecutivo de 10 líneas como máximo, una recomendación según el propósito y la lista priorizada de datos que más reducirían la incertidumbre.",
     "criterios": ["Tabla de rangos por método con pesos", "Rango final y valor central claros", "Recomendación accionable según el propósito"]},
]

GROUPS = ["Núcleo", "Mercado", "M&A", "Especial", "Personalizados"]
CORE = ["encargo", "financiero", "sector", "proyecciones", "wacc", "dcf", "comps", "sensibilidad", "critico", "sintesis"]

PRESETS: dict[str, dict] = {
    "pyme":  {"label": "Pyme no cotizada", "tipo": "empresa", "mods": CORE + ["due", "activos"]},
    "cotiz": {"label": "Cotizada", "tipo": "empresa", "mods": CORE + ["mercado", "due"]},
    "ma":    {"label": "M&A venta/compra", "tipo": "empresa", "mods": CORE + ["precedentes", "sinergias", "lbo", "due"]},
    "banca": {"label": "Banca / seguros", "tipo": "financiera",
              "mods": ["encargo", "financiero", "sector", "mercado", "ddm", "comps", "sotp", "due", "sensibilidad", "critico", "sintesis"]},
    "full":  {"label": "Completa", "tipo": "empresa", "mods": [c["id"] for c in CATALOG if c["id"] != "ddm"]},
}

TIPOS = {"empresa": "Empresa no financiera", "financiera": "Banco o aseguradora"}

NOTA_FINANCIERA = (
    "ES UNA ENTIDAD FINANCIERA. No uses FCFF, valor de empresa (EV) ni WACC: la deuda es materia prima del negocio, no financiación. "
    "Valora directamente el equity con el coste de los fondos propios (Ke). Métricas clave: margen de intereses, comisiones, eficiencia, "
    "coste del riesgo, ROTE, CET1 y exceso de capital, valor contable tangible por acción, payout y recompras. "
    "Métodos: descuento de dividendos con exceso de capital, P/VC tangible justificado = (ROTE − g)/(Ke − g) y comparables bancarios (P/VC tangible, PER)."
)

STATUS = {
    "pending":   ("En espera", "⚪"),
    "active":    ("Trabajando", "🔵"),
    "reviewing": ("Supervisor revisando", "🔵"),
    "hold":      ("Espera tu visto bueno", "🟠"),
    "approved":  ("Aprobado", "🟢"),
    "stale":     ("Desactualizado", "🟡"),
    "blocked":   ("Bloqueado", "🟣"),
    "error":     ("Error", "🔴"),
}

PROPOSITOS = [
    "Análisis de inversión en bolsa",
    "Venta de la empresa o de una participación",
    "Compra / adquisición",
    "Entrada de inversor o ronda",
    "Fairness opinion / informe independiente",
    "Fiscal, herencia o reestructuración societaria",
    "Gestión interna / planificación",
]

# Precios por millón de tokens (entrada, salida) y búsqueda web por unidad.
MODELS = {
    "claude-haiku-4-5": {"label": "Claude Haiku 4.5 (mínimo coste)", "in": 1.0, "out": 5.0},
    "claude-sonnet-5":  {"label": "Claude Sonnet 5 (equilibrado)", "in": 2.0, "out": 10.0},
    "claude-opus-5":    {"label": "Claude Opus 5 (máxima calidad)", "in": 5.0, "out": 25.0},
}
# Haiku 4.5 no admite razonamiento adaptativo, esfuerzo ni la búsqueda web con filtrado dinámico.
LEGACY_MODELS = {"claude-haiku-4-5"}
WEB_SEARCH_PRICE = 0.01
EFFORTS = {"low": "Baja (más barata)", "medium": "Media", "high": "Alta (recomendada)", "xhigh": "Muy alta", "max": "Máxima"}
