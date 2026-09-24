"""Motor de MAPS Valoración: prompts, llamadas a Claude, Supervisor y ejecución de la cadena."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Literal, Optional

import anthropic
from pydantic import BaseModel

from . import storage
from .catalog import CATALOG, LEGACY_MODELS, MODELS, NOTA_FINANCIERA, STATUS, WEB_SEARCH_PRICE

FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_ATTEMPTS = 2


class MapsError(Exception):
    """Error mostrable al usuario."""


# ─────────────────────────── utilidades de estado ───────────────────────────

def today() -> str:
    return dt.date.today().isoformat()


def now_t() -> str:
    return dt.datetime.now().strftime("%H:%M:%S")


def def_of(aid: str, customs: list[dict]) -> dict | None:
    return next((c for c in CATALOG if c["id"] == aid), None) or next((c for c in customs if c["id"] == aid), None)


def chain(p: dict, customs: list[dict]) -> list[dict]:
    on = set(p.get("modulos", []))
    lst = [c for c in CATALOG if c.get("fixed") or c["id"] in on]
    for c in customs:
        if c["id"] not in on:
            continue
        idx = next((i for i, d in enumerate(lst) if d["id"] == c.get("despues")), None)
        if idx is None:
            idx = next((i for i, d in enumerate(lst) if d["id"] == "critico"), len(lst) - 1) - 1
        lst.insert(idx + 1, {**c, "grupo": "Personalizados"})
    return lst


def agent(p: dict, aid: str) -> dict:
    return p.setdefault("agentes", {}).setdefault(aid, {
        "status": "pending", "output": "", "attempts": 0, "score": None, "sup_feedback": "",
        "sup_verdict": "", "human_feedback": "", "human_note": "", "last_rejected": None, "error": "", "fuentes": [],
    })


def add_log(p: dict, tag: str, msg: str, kind: str = "ceo") -> None:
    p.setdefault("log", []).append({"t": now_t(), "tag": tag, "msg": msg, "kind": kind})
    p["log"] = p["log"][-150:]


def section(text: str, name: str) -> str:
    m = re.search(rf"^#{{1,4}}\s*{re.escape(name)}\s*$", text or "", re.I | re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^#{1,2}\s+\S", rest, re.M)
    return (rest[: n.start()] if n else rest).strip()


def missing_by_agent(p: dict, customs: list[dict]) -> list[tuple[str, str]]:
    out = []
    for d in chain(p, customs):
        t = section(agent(p, d["id"]).get("output", ""), "Datos que faltan")
        if t and not re.match(r"^ninguno", t.strip(), re.I):
            out.append((d["nombre"], t))
    return out


def invalidate_from(p: dict, customs: list[dict], idx: int) -> None:
    for d in chain(p, customs)[idx:]:
        s = agent(p, d["id"])
        if s["status"] in ("approved", "hold"):
            s["status"] = "stale"
    p["resumen"] = None


def add_lesson(memoria: dict, aid: str, texto: str, origen: str, empresa: str) -> None:
    texto = (texto or "").strip()
    if not texto:
        return
    ls = memoria.setdefault(aid, [])
    if any(l["texto"].lower() == texto.lower() for l in ls):
        return
    ls.append({"texto": texto, "fecha": today(), "empresa": empresa, "origen": origen})
    memoria[aid] = ls[-25:]
    storage.save_memoria(memoria)


# ─────────────────────────── llamadas a Claude ───────────────────────────

@dataclass
class Settings:
    model: str = "claude-haiku-4-5"
    effort: str = "low"


@dataclass
class CallResult:
    text: str
    sources: list[dict] = field(default_factory=list)
    searches: int = 0
    cost: float = 0.0
    truncated: bool = False


def _cost(model: str, usage) -> float:
    pr = MODELS.get(model, MODELS["claude-opus-5"])
    cin = (usage.input_tokens or 0) + 1.25 * (getattr(usage, "cache_creation_input_tokens", 0) or 0) \
        + 0.1 * (getattr(usage, "cache_read_input_tokens", 0) or 0)
    c = cin * pr["in"] / 1e6 + (usage.output_tokens or 0) * pr["out"] / 1e6
    stu = getattr(usage, "server_tool_use", None)
    if stu is not None:
        c += (getattr(stu, "web_search_requests", 0) or 0) * WEB_SEARCH_PRICE
    return c


def _model_kwargs(s: Settings, max_tokens: int) -> dict:
    """Parámetros según el modelo: Haiku 4.5 va sin razonamiento, sin esfuerzo y sin fallbacks."""
    if s.model in LEGACY_MODELS:
        return dict(model=s.model, max_tokens=min(max_tokens, 16000))
    return dict(model=s.model, max_tokens=max_tokens, thinking={"type": "adaptive"},
                output_config={"effort": s.effort}, betas=[FALLBACK_BETA], fallbacks="default")


def _web_tool(s: Settings, uses: int) -> dict:
    kind = "web_search_20250305" if s.model in LEGACY_MODELS else "web_search_20260209"
    return {"type": kind, "name": "web_search", "max_uses": uses}


def _api_error(e: Exception) -> MapsError:
    if isinstance(e, anthropic.AuthenticationError):
        return MapsError("La API key no es válida. Revísala en la barra lateral.")
    if isinstance(e, anthropic.PermissionDeniedError):
        return MapsError("Tu API key no tiene permiso para este modelo o esta función.")
    if isinstance(e, anthropic.RateLimitError):
        return MapsError("Límite de uso de la API alcanzado. Espera un minuto y pulsa Continuar.")
    if isinstance(e, anthropic.BadRequestError):
        return MapsError(f"Petición rechazada por la API: {e.message}")
    if isinstance(e, anthropic.APIStatusError):
        return MapsError(f"Error del servidor de Anthropic ({e.status_code}). Pulsa Reintentar.")
    if isinstance(e, anthropic.APIConnectionError):
        return MapsError("Sin conexión con la API de Anthropic. Revisa tu internet y reintenta.")
    return MapsError(str(e))


def call_stream(client: anthropic.Anthropic, s: Settings, *, system: str, content: list[dict],
                web_uses: int = 0, on_text=None, on_search=None) -> CallResult:
    """Llamada en streaming. Con web_uses>0 Claude puede buscar en internet.
    Devuelve solo el texto escrito tras la última búsqueda (el análisis final)."""
    messages: list[dict] = [{"role": "user", "content": content}]
    res = CallResult(text="")
    answer: list[str] = []
    sources: dict[str, str] = {}
    try:
        for _ in range(8):  # continuaciones por pause_turn
            kwargs = dict(_model_kwargs(s, 64000), system=system, messages=messages)
            if web_uses:
                kwargs["tools"] = [_web_tool(s, web_uses)]
            with client.beta.messages.stream(**kwargs) as stream:
                for ev in stream:
                    if ev.type == "content_block_start" and ev.content_block.type == "server_tool_use":
                        res.searches += 1
                        answer.clear()
                        if on_search:
                            on_search(res.searches)
                    elif ev.type == "content_block_delta" and ev.delta.type == "text_delta":
                        answer.append(ev.delta.text)
                        if on_text:
                            on_text("".join(answer))
                msg = stream.get_final_message()
            res.cost += _cost(s.model, msg.usage)
            for b in msg.content:
                if b.type == "web_search_tool_result" and isinstance(b.content, list):
                    for r in b.content:
                        url = getattr(r, "url", None)
                        if url:
                            sources.setdefault(url, getattr(r, "title", "") or url)
                elif b.type == "text":
                    for c in getattr(b, "citations", None) or []:
                        url = getattr(c, "url", None)
                        if url:
                            sources.setdefault(url, getattr(c, "title", "") or url)
            if msg.stop_reason == "refusal":
                raise MapsError("Claude ha rechazado esta petición. Reformula las indicaciones o la información aportada.")
            if msg.stop_reason == "pause_turn":
                messages = messages + [{"role": "assistant", "content": msg.content}]
                continue
            res.truncated = msg.stop_reason == "max_tokens"
            break
    except anthropic.APIError as e:
        raise _api_error(e) from e
    res.text = "".join(answer).strip()
    res.sources = [{"url": u, "titulo": t} for u, t in sources.items()]
    if not res.text:
        raise MapsError("Claude no devolvió texto. Reintenta.")
    return res


def call_parse(client: anthropic.Anthropic, s: Settings, prompt: str, schema: type[BaseModel]):
    """Llamada con salida estructurada (JSON validado contra el esquema Pydantic)."""
    try:
        r = client.beta.messages.parse(
            **_model_kwargs(s, 16000), messages=[{"role": "user", "content": prompt}], output_format=schema,
        )
    except anthropic.APIError as e:
        raise _api_error(e) from e
    if r.stop_reason == "refusal":
        raise MapsError("Claude ha rechazado esta petición.")
    if r.parsed_output is None:
        raise MapsError("La respuesta no tenía el formato esperado. Reintenta.")
    return r.parsed_output, _cost(s.model, r.usage)


class Verdict(BaseModel):
    veredicto: Literal["aprobar", "rechazar"]
    puntuacion: int
    feedback: str
    leccion: str


class Route(BaseModel):
    resumen: str
    afectados: list[str]


class Metodo(BaseModel):
    metodo: str
    min: float
    max: float


class Rango(BaseModel):
    min: float
    max: float
    central: float


class Football(BaseModel):
    moneda: str
    unidad: str
    metodos: list[Metodo]
    final: Rango
    por_accion: Optional[Rango]
    precio_actual: Optional[float]
    frase: str


# ─────────────────────────── prompts ───────────────────────────

SYSTEM = """Eres un especialista dentro de MAPS, un sistema multi-agente de valoración de empresas. Trabajáis en cadena: cada especialista recibe el trabajo ya aprobado de los anteriores (el Testigo), produce su parte y un Supervisor la revisa.

Reglas:
- Usa la información aportada y el Testigo. Si recurres a conocimiento general (primas de riesgo habituales, múltiplos sectoriales típicos…), márcalo con [SUPUESTO] y explica el orden de magnitud. Nunca inventes cifras de la empresa.
- Si tienes búsqueda web, úsala solo para datos concretos que falten o estén desactualizados, y cita la fuente y la fecha de cada cifra obtenida. No narres las búsquedas: escribe solo el análisis final.
- Muestra los cálculos en tablas markdown, con unidad y moneda en cada cifra.
- Sé concreto y denso: unas 900-1200 palabras como máximo.
- Sé coherente con el Testigo; si discrepas de un especialista anterior, dilo y cuantifica el efecto.
- Termina SIEMPRE con estas dos secciones exactas:
## Conclusión clave
(2-5 líneas con las cifras que necesita el siguiente especialista)
## Datos que faltan
(lista de datos concretos que mejorarían tu análisis, o "Ninguno")
- Escribe en español."""


def empresa_header(p: dict) -> str:
    h = (f"EMPRESA: {p['nombre']}" + (f" (cotiza, ticker {p.get('ticker') or '—'})" if p.get("cotiza") else " (no cotiza)") +
         f"\nTIPO: {'Entidad financiera' if p.get('tipo') == 'financiera' else 'Empresa no financiera'}"
         f"\nSECTOR: {p.get('sector') or 'no indicado'} · PAÍS: {p.get('pais') or 'no indicado'} · MONEDA: {p.get('moneda') or 'EUR'}"
         f"\nPROPÓSITO: {p.get('proposito') or 'no indicado'}\nFECHA DE VALORACIÓN: {p.get('fecha') or today()}")
    if p.get("tipo") == "financiera":
        h += f"\n\n{NOTA_FINANCIERA}"
    if p.get("notas"):
        h += f"\n\nNOTAS DEL CEO: {p['notas']}"
    return h


def info_block(p: dict, cap: int = 60000) -> str:
    parts, used = [], 0
    for d in p.get("info", []):
        t = (d.get("resumen") or d.get("texto") or "").strip()[:20000]
        if not t:
            continue
        t = t[: max(0, cap - used)]
        if not t:
            break
        src = f" — fuentes: {', '.join(f['url'] for f in d.get('fuentes', [])[:8])}" if d.get("fuentes") else ""
        parts.append(f"### {d['titulo']} ({d.get('fecha', '')}){' — extracto' if d.get('resumen') else ''}{src}\n{t}")
        used += len(t)
    return "\n\n".join(parts) or "(Aún no hay información aportada. Trabaja con supuestos marcados y pide los datos.)"


def testigo_block(p: dict, customs: list[dict], d: dict, cap: int = 80000) -> str:
    ch = chain(p, customs)
    idx = next(i for i, x in enumerate(ch) if x["id"] == d["id"])
    prev = [x for x in ch[:idx] if agent(p, x["id"])["output"] and agent(p, x["id"])["status"] in ("approved", "stale", "hold")]
    if not prev:
        return "(Eres el primero de la cadena.)"
    per = max(2000, cap // len(prev))
    out = []
    for x in prev:
        o = agent(p, x["id"])["output"]
        if len(o) > per:
            cc = section(o, "Conclusión clave")
            o = o[: max(500, per - len(cc) - 100)] + "\n[…recortado…]\n## Conclusión clave\n" + cc
        out.append(f"### {x['nombre']}\n{o}")
    return "\n\n".join(out)


def build_content(p: dict, customs: list[dict], memoria: dict, d: dict) -> list[dict]:
    """Bloque 1 (empresa + información) con caché: es idéntico para todos los especialistas de la cadena."""
    s = agent(p, d["id"])
    shared = f"{empresa_header(p)}\n\nINFORMACIÓN APORTADA:\n{info_block(p)}"
    task = (f'Eres "{d["nombre"]}".\n\nTU TAREA:\n{d["tarea"]}\n\nCRITERIOS CON LOS QUE TE EVALUARÁ EL SUPERVISOR:\n'
            + "\n".join(f"- {c}" for c in d.get("criterios", [])))
    lessons = memoria.get(d["id"], [])[-12:]
    if lessons:
        task += "\n\nLECCIONES APRENDIDAS EN VALORACIONES ANTERIORES (aplícalas):\n" + "\n".join(f"- {l['texto']}" for l in lessons)
    task += f"\n\nTESTIGO — TRABAJO APROBADO DE LOS ESPECIALISTAS ANTERIORES:\n{testigo_block(p, customs, d)}"
    if s.get("human_feedback"):
        task += f"\n\nINDICACIONES DEL CEO (humano), prioridad máxima:\n{s['human_feedback']}"
    if s.get("human_note"):
        task += f"\n\nORIENTACIÓN DEL CEO TRAS EL BLOQUEO:\n{s['human_note']}"
    if s.get("last_rejected"):
        lr = s["last_rejected"]
        task += (f"\n\nTU INTENTO ANTERIOR FUE RECHAZADO.\nFeedback: {lr['feedback']}\nCorrige exactamente eso. "
                 f"Intento anterior (resumido):\n{lr['output'][:6000]}")
    task += "\n\nEscribe ahora tu análisis."
    return [{"type": "text", "text": shared, "cache_control": {"type": "ephemeral"}}, {"type": "text", "text": task}]


def sup_prompt(p: dict, customs: list[dict], d: dict, out: str) -> str:
    ch = chain(p, customs)
    idx = next(i for i, x in enumerate(ch) if x["id"] == d["id"])
    prev = []
    for x in ch[:idx]:
        cc = section(agent(p, x["id"])["output"], "Conclusión clave")
        if cc:
            prev.append(f"- {x['nombre']}: {' '.join(cc.split())[:600]}")
    return f"""Eres el SUPERVISOR de MAPS, un sistema multi-agente de valoración de empresas. Revisa el trabajo de un especialista.

{empresa_header(p)}

ESPECIALISTA: {d['nombre']}
TAREA ENCARGADA: {d['tarea']}
CRITERIOS:
{chr(10).join('- ' + c for c in d.get('criterios', []))}

CONCLUSIONES YA APROBADAS DE ESPECIALISTAS ANTERIORES:
{chr(10).join(prev) or '(ninguna)'}

OUTPUT A REVISAR:
\"\"\"
{out[:40000]}
\"\"\"

Aprueba si cumple razonablemente la tarea y los criterios. Rechaza SOLO por problemas materiales: errores de cálculo, incoherencia no justificada con las conclusiones anteriores, cifras de la empresa inventadas sin fuente ni marca [SUPUESTO], ausencia de las secciones "Conclusión clave" o "Datos que faltan", o no hacer la tarea. La falta de datos NO es motivo de rechazo si se declara y se usan supuestos razonables.

- puntuacion: 0-10.
- feedback: máximo 3 frases concretas.
- leccion: una regla general, reutilizable en OTRAS valoraciones por este especialista, solo si has detectado un fallo generalizable; si no, cadena vacía."""


# ─────────────────────────── ejecución de la cadena ───────────────────────────

class Hooks:
    """Callbacks de la interfaz. La app de Streamlit los sobreescribe."""
    def agent_start(self, d, attempt): ...
    def text(self, d, text): ...
    def search(self, d, n): ...
    def reviewing(self, d): ...
    def verdict(self, d, s): ...
    def save(self): ...


@dataclass
class Ctx:
    client: anthropic.Anthropic
    settings: Settings
    customs: list[dict]
    memoria: dict


def run_chain(ctx: Ctx, p: dict, start: int = 0, hooks: Hooks | None = None) -> str:
    """Ejecuta la cadena desde `start`. Devuelve 'complete', 'hold', 'blocked' o 'error'."""
    hooks = hooks or Hooks()
    ch = chain(p, ctx.customs)
    for d in ch[start:]:
        s = agent(p, d["id"])
        if s["status"] == "approved":
            continue
        if s["status"] == "hold":
            return "hold"
        r = run_agent(ctx, p, d, hooks)
        if r != "approved":
            return r
    if all(agent(p, d["id"])["status"] == "approved" for d in chain(p, ctx.customs)):
        add_log(p, "CEO", "Cadena completada. Valoración lista.")
        p["estado"] = "complete"
        hooks.save()
        return "complete"
    return "hold"


def run_agent(ctx: Ctx, p: dict, d: dict, hooks: Hooks) -> str:
    s = agent(p, d["id"])
    web = int(p.get("web_uses", 2)) if p.get("web_especialistas", False) else 0
    while True:
        s.update(status="active", error="")
        add_log(p, "ESP", f"[{d['nombre']}] trabajando" + (f" (intento {s['attempts'] + 1}/{MAX_ATTEMPTS})" if s["attempts"] else "") + "…", "esp")
        hooks.save()
        hooks.agent_start(d, s["attempts"])
        try:
            r = call_stream(ctx.client, ctx.settings, system=SYSTEM, content=build_content(p, ctx.customs, ctx.memoria, d),
                            web_uses=web, on_text=lambda t: hooks.text(d, t), on_search=lambda n: hooks.search(d, n))
        except MapsError as e:
            s.update(status="error", error=str(e))
            add_log(p, "ERR", f"[{d['nombre']}] {e}", "rej")
            hooks.save()
            return "error"
        p["coste"] = p.get("coste", 0) + r.cost
        s["output"] = r.text + ("\n\n> ⚠️ Respuesta cortada por longitud." if r.truncated else "")
        s["fuentes"] = r.sources
        s["status"] = "reviewing"
        add_log(p, "ESP", f"[{d['nombre']}] output enviado al SUPERVISOR" + (f" ({r.searches} búsquedas web)" if r.searches else "") + ".", "esp")
        hooks.save()
        hooks.reviewing(d)
        try:
            v, cost = call_parse(ctx.client, ctx.settings, sup_prompt(p, ctx.customs, d, s["output"]), Verdict)
        except MapsError as e:
            s.update(status="error", error=f"Supervisor: {e}")
            add_log(p, "ERR", s["error"], "rej")
            hooks.save()
            return "error"
        p["coste"] = p.get("coste", 0) + cost
        s.update(score=max(0, min(10, v.puntuacion)), sup_feedback=v.feedback, sup_verdict=v.veredicto)
        if v.veredicto == "aprobar":
            s.update(last_rejected=None, human_note="")
            if p.get("revision"):
                s["status"] = "hold"
            else:
                s.update(status="approved", human_feedback="")
            add_log(p, "SUPERVISOR", f"[{d['nombre']}] aprobado ({s['score']}/10)." + (" Espera tu visto bueno." if p.get("revision") else ""), "sup")
            hooks.save()
            hooks.verdict(d, s)
            return "hold" if p.get("revision") else "approved"
        s["attempts"] += 1
        s["last_rejected"] = {"feedback": v.feedback, "output": s["output"][:6000]}
        if v.leccion:
            add_lesson(ctx.memoria, d["id"], v.leccion, "Supervisor", p["nombre"])
        hooks.verdict(d, s)
        if s["attempts"] >= MAX_ATTEMPTS:
            s["status"] = "blocked"
            add_log(p, "SUPERVISOR", f"LÍMITE DE {MAX_ATTEMPTS} INTENTOS en [{d['nombre']}]. Se requiere tu intervención.", "rej")
            hooks.save()
            return "blocked"
        add_log(p, "SUPERVISOR", f"[{d['nombre']}] rechazado ({s['attempts']}/{MAX_ATTEMPTS}): {v.feedback}", "rej")
        hooks.save()


# ─────────────────────────── información e investigación ───────────────────────────

def research_prompt(p: dict, encargo: str) -> str:
    return f"""Eres el investigador de MAPS, un sistema de valoración de empresas. Busca en la web datos públicos y actuales para valorar esta empresa.

{empresa_header(p)}

QUÉ BUSCAR:
{encargo}

Reglas:
- Prioriza fuentes primarias (web de relaciones con inversores de la empresa, informes de resultados, CNMV/SEC, bancos centrales, bolsas) y después prensa financiera reconocida.
- Cada cifra con su fecha y su fuente (nombre y URL). Si dos fuentes discrepan, muestra ambas.
- Presenta los datos en tablas markdown agrupadas por tema. No valores la empresa: solo reúne datos.
- Termina con "## No encontrado" listando lo que no hayas podido localizar.
- No narres las búsquedas. Escribe en español."""


def encargo_inicial(p: dict) -> str:
    if p.get("tipo") == "financiera":
        return ("- Últimos resultados publicados (trimestrales y anuales): margen de intereses, comisiones, costes, eficiencia, coste del riesgo, beneficio, ROTE, CET1, morosidad.\n"
                "- Guía y objetivos del plan estratégico vigente (ROTE, reparto de dividendos y recompras).\n"
                "- Cotización actual, número de acciones, capitalización, valor contable tangible por acción, dividendo por acción y rentabilidad.\n"
                "- Consenso de analistas (precio objetivo, recomendaciones) si está disponible.\n"
                "- Comparables del sector: P/VC tangible, PER, ROTE y CET1 de 5-6 bancos o aseguradoras comparables.\n"
                "- Rentabilidad del bono a 10 años del país, tipos del banco central y estimaciones de prima de riesgo de mercado.")
    if p.get("cotiza"):
        return ("- Últimos resultados (anuales y trimestrales): ventas, EBITDA, EBIT, beneficio neto, flujo de caja libre, deuda neta.\n"
                "- Guía de la compañía y objetivos del plan estratégico.\n"
                "- Cotización actual, número de acciones, capitalización, valor de empresa, beta, dividendo.\n"
                "- Consenso de analistas (estimaciones y precio objetivo).\n"
                "- Comparables cotizados con sus múltiplos (EV/EBITDA, EV/Ventas, PER) y crecimiento.\n"
                "- Transacciones recientes del sector con múltiplos pagados.\n"
                "- Bono a 10 años del país y prima de riesgo de mercado estimada.")
    return ("- Cualquier dato financiero público de la empresa (cuentas depositadas, notas de prensa, ranking sectorial, ventas, empleados).\n"
            "- Noticias relevantes recientes de la empresa (inversiones, clientes, litigios, cambios de propiedad).\n"
            "- Tamaño y crecimiento de su mercado.\n"
            "- Múltiplos de comparables cotizados del sector y transacciones recientes con múltiplos pagados.\n"
            "- Bono a 10 años del país, prima de riesgo de mercado y primas por tamaño habituales.")


def research(ctx: Ctx, p: dict, encargo: str, titulo: str, on_text=None, on_search=None) -> dict:
    r = call_stream(ctx.client, ctx.settings, system="Eres un investigador financiero riguroso.",
                    content=[{"type": "text", "text": research_prompt(p, encargo)}],
                    web_uses=int(p.get("web_uses_research", 5)), on_text=on_text, on_search=on_search)
    p["coste"] = p.get("coste", 0) + r.cost
    doc = {"id": storage.new_id("i_"), "titulo": titulo, "texto": r.text, "fecha": today(),
           "origen": "web", "fuentes": r.sources, "resumen": ""}
    p.setdefault("info", []).append(doc)
    add_log(p, "CEO", f"Investigación web «{titulo}»: {r.searches} búsquedas, {len(r.sources)} fuentes.", "ceo")
    return doc


def add_info(ctx: Ctx | None, p: dict, titulo: str, texto: str, origen: str = "manual") -> dict:
    texto = (texto or "").strip()
    if not texto:
        raise MapsError("Pega algún contenido o sube un archivo.")
    doc = {"id": storage.new_id("i_"), "titulo": titulo or f"Información {len(p.get('info', [])) + 1}",
           "texto": texto[:300000], "fecha": today(), "origen": origen, "fuentes": [], "resumen": ""}
    p.setdefault("info", []).append(doc)
    add_log(p, "CEO", f"Nueva información: «{doc['titulo']}» ({len(texto):,} caracteres).".replace(",", "."), "ceo")
    if ctx and len(texto) > 15000:
        r = call_stream(ctx.client, ctx.settings, system="Eres un analista financiero.", content=[{"type": "text", "text":
            f"Extrae de este documento toda la información útil para valorar {p['nombre']}: cifras financieras (con año, unidad y moneda) "
            f"en tablas markdown, datos operativos, clientes, deuda, capital, hechos relevantes y riesgos. No inventes nada. "
            f"Máximo 2000 palabras.\n\nDOCUMENTO: {doc['titulo']}\n{texto[:400000]}"}])
        doc["resumen"] = r.text
        p["coste"] = p.get("coste", 0) + r.cost
    return doc


def route_info(ctx: Ctx, p: dict, doc: dict) -> dict | None:
    """Decide qué especialistas deben rehacer su trabajo con la nueva información."""
    ch = chain(p, ctx.customs)
    if not any(agent(p, d["id"])["output"] for d in ch):
        return None
    lista = "\n".join(f"{d['id']} — {d['nombre']} — {d['tarea'][:160]}" for d in ch)
    r, cost = call_parse(ctx.client, ctx.settings,
        f"Nueva información para la valoración de {p['nombre']}:\n\"\"\"\n{(doc.get('resumen') or doc['texto'])[:12000]}\n\"\"\"\n\n"
        f"Especialistas de la cadena, en orden (id — nombre — tarea):\n{lista}\n\n"
        "¿Qué especialistas deberían rehacer su trabajo con esta información? Devuelve un resumen de una frase de lo que aporta "
        "y la lista de ids afectados (vacía si no cambia nada).", Route)
    p["coste"] = p.get("coste", 0) + cost
    ids = [i for i in r.afectados if any(d["id"] == i for d in ch)]
    if not ids:
        return None
    return {"resumen": r.resumen, "afectados": ids, "desde": next(i for i, d in enumerate(ch) if d["id"] in ids)}


def extract_football(ctx: Ctx, p: dict) -> dict | None:
    out = agent(p, "sintesis")["output"]
    if not out:
        return None
    r, cost = call_parse(ctx.client, ctx.settings,
        f"Del siguiente informe de síntesis de la valoración de {p['nombre']}, extrae los rangos de valor del EQUITY por método "
        "(en la misma unidad para todos, p. ej. M = millones), el rango final con su valor central, el valor por acción si aparece, "
        "el precio actual por acción si aparece, y una frase de conclusión.\n\n" + out[:40000], Football)
    p["coste"] = p.get("coste", 0) + cost
    p["resumen"] = r.model_dump()
    return p["resumen"]


def report_md(p: dict, customs: list[dict]) -> str:
    m = f"# Valoración de {p['nombre']}\n\n" + "\n".join(f"- {l}" for l in empresa_header(p).split("\n") if l.strip()) + "\n\n"
    r = p.get("resumen")
    if r:
        m += (f"## Rango de valor del equity\n\n**{r['final']['min']:,.1f} – {r['final']['max']:,.1f} {r['unidad']} {r['moneda']}** "
              f"(central {r['final']['central']:,.1f})\n\n{r.get('frase', '')}\n\n| Método | Mín | Máx |\n|---|---:|---:|\n"
              + "\n".join(f"| {x['metodo']} | {x['min']:,.1f} | {x['max']:,.1f} |" for x in r["metodos"]) + "\n\n")
    for d in chain(p, customs):
        s = agent(p, d["id"])
        if not s["output"]:
            continue
        m += f"---\n\n## {d['nombre']}" + (f" _({STATUS[s['status']][0]})_" if s["status"] != "approved" else "") + f"\n\n{s['output']}\n\n"
        if s.get("fuentes"):
            m += "**Fuentes:**\n" + "\n".join(f"- [{f['titulo']}]({f['url']})" for f in s["fuentes"]) + "\n\n"
    fuentes_info = [d for d in p.get("info", []) if d.get("fuentes")]
    if fuentes_info:
        m += "---\n\n## Fuentes de la investigación web\n\n"
        for d in fuentes_info:
            m += f"**{d['titulo']}**\n" + "\n".join(f"- [{f['titulo']}]({f['url']})" for f in d["fuentes"]) + "\n\n"
    return m + f"---\n\n_Generado con MAPS Valoración · {dt.datetime.now():%d/%m/%Y %H:%M}_\n"
