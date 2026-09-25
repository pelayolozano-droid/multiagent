"""MAPS Valoración — sistema multi-agente de valoración de empresas (Streamlit).

Ejecutar:  .venv\\Scripts\\streamlit run app.py
"""
from __future__ import annotations

import os
import time

import anthropic
import plotly.graph_objects as go
import streamlit as st

from maps import engine as E
from maps import market, storage
from maps.catalog import CATALOG, EFFORTS, GROUPS, LEGACY_MODELS, MODELS, PRESETS, PROPOSITOS, STATUS, TIPOS
from maps.files import read_upload

st.set_page_config(page_title="MAPS Valoración", page_icon="📊", layout="wide")
st.markdown("""<style>
.block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1400px;}
h1, h2, h3, h4 {letter-spacing: -0.01em;}
[data-testid="stMetricValue"] {font-size: 1.3rem;}
[data-testid="stMetricLabel"] p {font-size: .85rem;}
/* Lista de especialistas: botones alineados a la izquierda, compactos */
.st-key-agent_list [data-testid="stVerticalBlock"] {gap: .3rem;}
.st-key-agent_list button {justify-content: flex-start; text-align: left; min-height: 2.5rem; padding: .35rem .8rem;}
.st-key-agent_list button p {font-size: .92rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
/* Foco visible para quien navega con teclado */
button:focus-visible, [role="tab"]:focus-visible, [role="radio"]:focus-visible, a:focus-visible {
  outline: 3px solid #2447D6 !important; outline-offset: 2px; }
/* Etiqueta de estado: color + texto, nunca solo color */
.maps-badge {display: inline-flex; align-items: center; gap: .4rem; padding: .15rem .65rem; border-radius: 999px;
  font-size: .85rem; font-weight: 600; border: 1.5px solid var(--c); line-height: 1.5;}
.maps-badge::before {content: ""; width: .55rem; height: .55rem; border-radius: 50%; background: var(--c);}
.maps-meta {opacity: .8; font-size: .9rem;}
</style>""", unsafe_allow_html=True)
ss = st.session_state
for k, v in {"page": "main", "nav_radio": "Cadena", "route": None, "flash": None, "model": "claude-haiku-4-5", "effort": "low"}.items():
    ss.setdefault(k, v)

NAV = ["Cadena", "Información", "Informe", "Memoria", "Configuración"]
customs = storage.load_customs()
memoria = storage.load_memoria()


def md(text: str) -> str:
    """Evita que Streamlit interprete los $ como fórmulas LaTeX."""
    return (text or "").replace("$", "\\$")


def fmt(n) -> str:
    if n is None:
        return "–"
    return f"{n:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def flash(kind: str, msg: str) -> None:
    ss.flash = (kind, msg)


# Colores de estado con contraste suficiente en tema claro y oscuro; siempre van acompañados de texto.
STATUS_COLOR = {"pending": "#8A94A6", "active": "#2F6FEB", "reviewing": "#2F6FEB", "hold": "#D97706",
                "approved": "#16A34A", "stale": "#CA8A04", "blocked": "#9333EA", "error": "#DC2626"}


def badge(status: str) -> str:
    return f'<span class="maps-badge" style="--c:{STATUS_COLOR[status]}">{STATUS[status][0]}</span>'


def icono(d: dict) -> str:
    return d.get("icono", "🧩")


def resumen(d: dict) -> str:
    """Qué hace el especialista, en una frase (tooltip). Los personalizados usan el inicio de su tarea."""
    if d.get("resumen"):
        return d["resumen"]
    t = d.get("tarea", "")
    return t if len(t) < 180 else t[:177] + "…"


# ─────────────────────────── cliente de Claude ───────────────────────────

def get_ctx() -> E.Ctx | None:
    key = ss.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        try:
            key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            key = None
    if not key:
        return None
    client = anthropic.Anthropic(api_key=key, max_retries=3)
    return E.Ctx(client=client, settings=E.Settings(model=ss.model, effort=ss.effort), customs=customs, memoria=memoria)


# ─────────────────────────── barra lateral ───────────────────────────

COSTE_CADENA = {"claude-haiku-4-5": "~0,3-0,8 $", "claude-sonnet-5": "~1,5-4 $", "claude-opus-5": "~3-10 $"}

companies = storage.list_companies()
with st.sidebar:
    st.markdown("### 📊 MAPS Valoración")
    st.caption("Valoración de empresas con un equipo de especialistas de IA. Tú diriges como CEO.")
    if "cid_next" in ss:
        ss.cid = ss.pop("cid_next")
    if companies:
        ids = [c["id"] for c in companies]
        if ss.get("cid") not in ids:
            ss.cid = ids[0]
        st.selectbox("Empresa", ids, key="cid", format_func=lambda i: next(c["nombre"] for c in companies if c["id"] == i))
    if st.button("Nueva empresa", icon=":material/add:", use_container_width=True):
        ss.page = "nueva"
        st.rerun()

    st.divider()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.text_input("API key de Anthropic", type="password", key="api_key",
                      help="Se crea en console.anthropic.com. Solo se guarda mientras esta pestaña esté abierta. "
                           "También puedes definir la variable de entorno ANTHROPIC_API_KEY o .streamlit/secrets.toml.")
    ctx = get_ctx()
    if not ctx:
        st.info("Sin API key puedes preparar empresas e información, pero no ejecutar a los especialistas.", icon=":material/key:")

    with st.expander("Modelo y coste", icon=":material/tune:"):
        st.selectbox("Modelo", list(MODELS), key="model", format_func=lambda m: MODELS[m]["label"],
                     help="Haiku es el más barato; Sonnet y Opus razonan más y muestran su razonamiento, pero cuestan más.")
        st.selectbox("Esfuerzo de razonamiento", list(EFFORTS), key="effort", format_func=lambda e: EFFORTS[e],
                     disabled=ss.model in LEGACY_MODELS, help="Cuánto piensa el modelo antes de responder. Haiku 4.5 no razona: no le afecta.")
        st.caption(f"Coste orientativo de una cadena completa con este modelo: **{COSTE_CADENA.get(ss.model, '?')}**.")

P = storage.load_company(ss.cid) if companies and ss.get("cid") else None
if P:
    # Un run interrumpido (Detener o recarga) deja agentes a medias: se normalizan.
    dirty = False
    for s in P.get("agentes", {}).values():
        if s.get("status") in ("active", "reviewing"):
            s["status"] = "stale" if s.get("output") else "pending"
            dirty = True
    if dirty:
        storage.save_company(P)
    with st.sidebar:
        st.metric("Gasto de API en esta empresa", f"{P.get('coste', 0):.2f} $",
                  help="Suma de todas las llamadas a Claude hechas para esta empresa. Yahoo Finance es gratis.")


def save() -> None:
    storage.save_company(P)


def ch() -> list[dict]:
    return E.chain(P, customs)


def apply_mods(new_mods: list[str]) -> None:
    before = [d["id"] for d in ch()]
    P["modulos"] = list(dict.fromkeys(new_mods))
    P["mods_v"] = P.get("mods_v", 0) + 1
    after = ch()
    first_new = next((i for i, d in enumerate(after) if d["id"] not in before), None)
    if first_new is not None:
        E.invalidate_from(P, customs, first_new + 1)
    save()


def request_run(idx: int = 0) -> None:
    ss.run_req = idx
    ss.goto = "Cadena"
    st.rerun()


# ─────────────────────────── nueva empresa ───────────────────────────

def company_fields(prefix: str, v: dict) -> dict:
    c1, c2 = st.columns(2)
    out = {
        "nombre": c1.text_input("Nombre de la empresa", v.get("nombre", ""), key=f"{prefix}nombre", placeholder="Ej.: CaixaBank"),
        "sector": c2.text_input("Sector / actividad", v.get("sector", ""), key=f"{prefix}sector", placeholder="Ej.: banca minorista y seguros"),
    }
    c1, c2, c3 = st.columns(3)
    out["pais"] = c1.text_input("País", v.get("pais", "España"), key=f"{prefix}pais")
    out["moneda"] = c2.text_input("Moneda", v.get("moneda", "EUR"), key=f"{prefix}moneda")
    out["fecha"] = c3.date_input("Fecha de valoración", value=E.dt.date.fromisoformat(v.get("fecha") or E.today()),
                                 key=f"{prefix}fecha").isoformat()
    c1, c2, c3 = st.columns(3)
    prop = v.get("proposito") or PROPOSITOS[0]
    out["proposito"] = c1.selectbox("Propósito", PROPOSITOS, index=PROPOSITOS.index(prop) if prop in PROPOSITOS else 0, key=f"{prefix}proposito")
    out["tipo"] = c2.selectbox("Tipo de entidad", list(TIPOS), index=list(TIPOS).index(v.get("tipo", "empresa")),
                               format_func=TIPOS.get, key=f"{prefix}tipo")
    out["ticker"] = c3.text_input("Ticker (si cotiza)", v.get("ticker", ""), key=f"{prefix}ticker", placeholder="Ej.: CABK.MC")
    out["cotiza"] = st.checkbox("Cotiza en bolsa", v.get("cotiza", False), key=f"{prefix}cotiza")
    out["notas"] = st.text_area("Notas para todos los especialistas (opcional)", v.get("notas", ""), key=f"{prefix}notas",
                                placeholder="Ej.: el comprador potencial es un grupo industrial francés; valorar solo el negocio en España…")
    return out


def page_new() -> None:
    st.title("Nueva empresa" if companies else "Valora una empresa con una cadena de especialistas")
    if not companies:
        st.markdown("Tú eres el **CEO**: defines la empresa y aportas información (o dejas que el investigador la busque en la web). "
                    "Cada **especialista** (Claude) hace su parte y le pasa el Testigo al siguiente; un **Supervisor** revisa cada "
                    "entrega y le pide rehacerla una vez si no cumple. Lo que se corrige se guarda como **lección** para las siguientes valoraciones.")
    with st.form("new_co"):
        data = company_fields("nc_", {})
        preset = st.selectbox("Plantilla de especialistas", list(PRESETS), format_func=lambda k: PRESETS[k]["label"],
                              help="Podrás activar o desactivar módulos después en Configuración.")
        yahoo = st.checkbox("Descargar datos de Yahoo Finance si pones ticker (gratis)", value=True)
        investigar = st.checkbox("Investigar también en la web con Claude (de pago: ~0,05-0,15 $)", value=False)
        ok = st.form_submit_button("Crear empresa", type="primary")
    if ok:
        if not data["nombre"].strip():
            st.error("Ponle nombre a la empresa.")
            return
        if preset == "banca":
            data["tipo"] = "financiera"
        p = {"id": storage.new_id("e_"), **data, "modulos": list(PRESETS[preset]["mods"]), "revision": False,
             "web_especialistas": False, "web_uses": 2, "web_uses_research": 5, "agentes": {}, "info": [], "log": [],
             "resumen": None, "estado": "setup", "coste": 0.0, "creado": E.today()}
        E.add_log(p, "CEO", f"Empresa creada: {p['nombre']} ({PRESETS[preset]['label']}).")
        if yahoo and p.get("ticker", "").strip():
            try:
                with st.spinner("Descargando datos de Yahoo Finance…"):
                    add_yahoo(p, p["ticker"], [])
            except E.MapsError as e:
                flash("warning", str(e))
        storage.save_company(p)
        ss.cid_next = p["id"]
        ss.page = "main"
        ss.goto = "Información"
        if investigar:
            ss.research_req = ("inicial", None)
        st.rerun()
    if companies and st.button("Cancelar"):
        ss.page = "main"
        st.rerun()


# ─────────────────────────── cadena ───────────────────────────

class UIHooks(E.Hooks):
    """Muestra en directo qué está haciendo cada especialista: fase, razonamiento, búsquedas y texto."""

    def __init__(self, box):
        self.box = box
        self.last = 0.0
        self.progress = box.progress(0.0, text="Preparando la cadena…")

    def _label(self, d, fase: str) -> str:
        return f"{icono(d)} **{d['nombre']}** · {fase}"

    def agent_start(self, d, attempt):
        chain_ = ch()
        i = next(k for k, x in enumerate(chain_) if x["id"] == d["id"])
        self.progress.progress(i / len(chain_), text=f"Especialista {i + 1} de {len(chain_)}: {d['nombre']}")
        self.d, self.writing = d, False
        fase = "leyendo la información y el trabajo de los anteriores" + (f" (intento {attempt + 1} de {E.MAX_ATTEMPTS})" if attempt else "")
        self.status = self.box.status(self._label(d, fase), expanded=True)
        self.status.caption(f"**Qué hace:** {resumen(d)}")
        self.ph_search = self.status.empty()
        self.ph_think = self.status.empty()
        self.ph = self.status.empty()
        self.ph.caption("Suele tardar entre 30 segundos y 3 minutos.")

    def thinking(self, d, t):
        if time.time() - self.last > 0.5:
            self.status.update(label=self._label(d, "razonando"))
            self.ph_think.info(f"**Razonando:** {md(t[-700:])}", icon=":material/psychology:")
            self.last = time.time()

    def text(self, d, t):
        if not self.writing:
            self.writing = True
            self.status.update(label=self._label(d, "escribiendo el análisis"))
            self.ph_think.empty()
        if time.time() - self.last > 0.3:
            self.ph.markdown(md(t))
            self.last = time.time()

    def search(self, d, n):
        self.writing = False
        self.status.update(label=self._label(d, f"buscando en la web ({n})"))
        self.ph_search.caption(f"Búsquedas web realizadas: {n}")

    def reviewing(self, d):
        self.ph.markdown(md(E.agent(P, d["id"])["output"]))
        self.status.update(label=self._label(d, "el Supervisor está revisando el trabajo"))

    def verdict(self, d, s):
        ok = s["sup_verdict"] == "aprobar"
        self.status.update(label=self._label(d, f"{'aprobado' if ok else 'rechazado'} por el Supervisor ({s['score']}/10)"),
                           state="complete" if ok else "error", expanded=False)

    def save(self):
        storage.save_company(P)


def execute_run(box, start: int) -> None:
    if not ctx:
        flash("error", "Añade tu API key en la barra lateral para ejecutar la cadena.")
        return
    P["estado"] = "running"
    box.button("⏹ Detener", help="Detiene la cadena. Lo aprobado se conserva.")
    res = E.run_chain(ctx, P, start, UIHooks(box))
    if res == "complete" and not P.get("resumen"):
        with box.spinner("Extrayendo el rango de valor para el football field…"):
            try:
                E.extract_football(ctx, P)
            except E.MapsError as e:
                flash("warning", f"No se pudo extraer el rango: {e}")
    P["estado"] = {"complete": "complete"}.get(res, "paused")
    save()
    msgs = {"complete": ("success", "Cadena completada. Mira el Informe."), "hold": ("info", "Un especialista espera tu visto bueno."),
            "blocked": ("warning", "Un especialista está bloqueado: necesita tu orientación."),
            "error": ("error", "La cadena se ha detenido por un error. Revisa el especialista marcado en rojo.")}
    flash(*msgs[res])
    st.rerun()


def metrics_row() -> None:
    chain_ = ch()
    ap = sum(E.agent(P, d["id"])["status"] == "approved" for d in chain_)
    r = P.get("resumen")
    c = st.columns(5)
    c[0].metric("Progreso", f"{ap} / {len(chain_)}", help="Especialistas aprobados")
    c[1].metric("Valor del equity", f"{fmt(r['final']['min'])}–{fmt(r['final']['max'])} {r['unidad']}" if r else "Pendiente")
    c[2].metric("Por acción", f"{fmt(r['por_accion']['central'])} {r['moneda']}" if r and r.get("por_accion") else "–")
    c[3].metric("Información", f"{len(P.get('info', []))} docs")
    c[4].metric("Datos que faltan", len(E.missing_by_agent(P, customs)))


def route_banner() -> None:
    r = ss.route
    if not r or r.get("cid") != P["id"]:
        return
    chain_ = ch()
    with st.container(border=True):
        st.markdown(f"**La nueva información afecta a la valoración.** {md(r['resumen'])}")
        st.caption("Afectados: " + ", ".join(E.def_of(i, customs)["nombre"] for i in r["afectados"] if E.def_of(i, customs))
                   + f". Se rehará la cadena desde «{chain_[r['desde']]['nombre']}».")
        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("Actualizar la valoración", type="primary"):
            E.invalidate_from(P, customs, r["desde"])
            for i in r["afectados"]:
                E.agent(P, i)["attempts"] = 0
            E.add_log(P, "CEO", f"Actualizando la valoración desde [{chain_[r['desde']]['nombre']}] con nueva información.")
            save()
            ss.route = None
            request_run(r["desde"])
        if c2.button("Ahora no"):
            ss.route = None
            st.rerun()


def page_chain() -> None:
    metrics_row()
    route_banner()
    chain_ = ch()
    first_todo = next((i for i, d in enumerate(chain_) if E.agent(P, d["id"])["status"] != "approved"), None)
    hold = next((d for d in chain_ if E.agent(P, d["id"])["status"] == "hold"), None)
    started = any(E.agent(P, d["id"])["status"] != "pending" for d in chain_)

    run_box = st.container()
    if "run_req" in ss:
        execute_run(run_box, ss.pop("run_req"))
        return

    c1, c2 = st.columns([1, 4], vertical_alignment="center")
    label = "Ejecutar cadena" if not started else ("Completada" if first_todo is None else "Continuar")
    if c1.button(label, type="primary", icon=":material/play_arrow:" if first_todo is not None else ":material/check:",
                 disabled=first_todo is None or hold is not None or not ctx, use_container_width=True,
                 help="Los especialistas trabajan uno tras otro; lo ya aprobado no se repite."):
        request_run(0)
    if hold:
        c2.info(f"«{hold['nombre']}» espera tu visto bueno.", icon=":material/front_hand:")
    elif not P.get("info") and not started:
        c2.caption("Aún no hay información: los especialistas trabajarán con supuestos. "
                   "Mejor añade datos en «Información» (Yahoo Finance es gratis).")

    ids = [d["id"] for d in chain_]
    if ss.get("sel") not in ids:
        ss.sel = next((d["id"] for d in chain_ if E.agent(P, d["id"])["status"] != "approved"), ids[0])

    left, right = st.columns([1, 2.6], gap="large")
    with left:
        st.markdown("**Especialistas**", help="Pasa el cursor sobre cada uno para ver qué hace. Púlsalo para ver su trabajo.")
        with st.container(key="agent_list"):
            for i, d in enumerate(chain_):
                stt = E.agent(P, d["id"])["status"]
                st.button(f"{STATUS[stt][1]} {i + 1} · {d['nombre']}", key=f"pick_{d['id']}", use_container_width=True,
                          type="primary" if d["id"] == ss.sel else "secondary",
                          help=f"**{icono(d)} {d['nombre']}**\n\n{resumen(d)}\n\nEstado: {STATUS[stt][0]}",
                          on_click=lambda aid=d["id"]: ss.update(sel=aid))
        with st.expander("Actividad de toda la cadena", icon=":material/history:"):
            for e in reversed(P.get("log", [])[-60:]):
                st.caption(f"`{e['t']}` **{e['tag']}** · {md(e['msg'])}")
    with right:
        agent_detail(chain_, ids.index(ss.sel))


def agent_detail(chain_: list[dict], idx: int) -> None:
    d = chain_[idx]
    s = E.agent(P, d["id"])
    with st.container(border=True):
        st.subheader(f"{icono(d)} {d['nombre']}", help=resumen(d), anchor=False)
        meta = [f"Especialista {idx + 1} de {len(chain_)}", d["grupo"]]
        if s.get("score") is not None:
            meta.append(f"Supervisor: {s['score']}/10")
        if s.get("attempts"):
            meta.append(f"Rechazos: {s['attempts']} de {E.MAX_ATTEMPTS}")
        st.markdown(f"{badge(s['status'])} &nbsp; <span class='maps-meta'>{' · '.join(meta)}</span>", unsafe_allow_html=True)
        st.markdown(f"*{resumen(d)}*")

        if s["status"] == "error":
            st.error(s.get("error") or "Algo falló.", icon=":material/error:")
        if s["status"] == "blocked":
            st.warning(f"El Supervisor ha rechazado este trabajo {E.MAX_ATTEMPTS} veces. Da una orientación concreta y reintenta, "
                       "o edita el resultado a mano.", icon=":material/block:")
        if s["status"] == "stale":
            st.info("Desactualizado: ha cambiado algo anterior en la cadena o la información. Se rehará al pulsar Continuar.",
                    icon=":material/update:")
        if s.get("sup_feedback"):
            (st.success if s["sup_verdict"] == "aprobar" else st.warning)(
                f"**Supervisor:** {md(s['sup_feedback'])}", icon=":material/verified:" if s["sup_verdict"] == "aprobar" else ":material/rule:")
        if s.get("human_feedback"):
            st.info(f"**Tus indicaciones:** {md(s['human_feedback'])}", icon=":material/person:")

        # Acciones principales
        prev_ok = all(E.agent(P, x["id"])["status"] == "approved" for x in chain_[:idx])
        cols = st.columns(3)
        if s["status"] == "hold" and cols[0].button("Dar visto bueno y continuar", type="primary", icon=":material/check:"):
            s.update(status="approved", human_feedback="")
            E.add_log(P, "CEO", f"Visto bueno a [{d['nombre']}].")
            save()
            request_run(0)
        if s["status"] == "error" and cols[0].button("Reintentar", type="primary", icon=":material/refresh:", disabled=not ctx):
            s["status"] = "stale" if s["output"] else "pending"
            save()
            request_run(idx)
        if s["status"] in ("stale", "pending") and idx > 0 and prev_ok and cols[1].button(
                "Ejecutar desde aquí", icon=":material/play_arrow:", disabled=not ctx):
            request_run(idx)

    tabs = st.tabs([":material/description: Análisis", ":material/psychology: Cómo lo ha decidido",
                    ":material/history: Actividad", ":material/info: Qué hace"])

    with tabs[0]:
        if s["output"]:
            body = E.without_sections(s["output"], ["Cómo lo he decidido", "Conclusión clave", "Datos que faltan"])
            conclusion = E.section(s["output"], "Conclusión clave")
            faltan = E.section(s["output"], "Datos que faltan")
            if conclusion:
                st.success(f"**Conclusión clave**\n\n{md(conclusion)}", icon=":material/flag:")
            st.markdown(md(body))
            if faltan and not faltan.lower().startswith("ninguno"):
                with st.expander("Datos que le faltan", icon=":material/help:"):
                    st.markdown(md(faltan))
            if s.get("fuentes"):
                with st.expander(f"Fuentes web ({len(s['fuentes'])})", icon=":material/link:"):
                    for f in s["fuentes"]:
                        st.markdown(f"- [{f['titulo']}]({f['url']})")
        else:
            st.caption("Todavía no ha trabajado. " + ("Está listo: pulsa Ejecutar o Continuar." if prev_ok
                                                      else "Espera el trabajo de los especialistas anteriores."))

    with tabs[1]:
        decision = E.section(s["output"], "Cómo lo he decidido") if s["output"] else ""
        if decision:
            st.markdown("##### Sus decisiones, explicadas por él mismo")
            st.markdown(md(decision))
        elif s["output"]:
            st.caption("Este trabajo se hizo antes de que existiera esta sección. Se generará la próxima vez que trabaje.")
        else:
            st.caption("Aquí verás qué decisiones ha tomado, qué ha descartado y por qué, cuando trabaje.")
        if s.get("pensamiento"):
            with st.expander("Resumen de su razonamiento interno", icon=":material/psychology:"):
                st.caption("Resumen que genera el propio modelo de lo que pensó antes de escribir.")
                st.markdown(md(s["pensamiento"]))
        elif s["output"] and s.get("modelo", ss.model) in LEGACY_MODELS:
            st.caption("Haiku 4.5 no genera razonamiento interno. Para verlo, usa Sonnet 5 u Opus 5 (más caros).")
        if s.get("last_rejected"):
            st.markdown("##### Por qué se rechazó el intento anterior")
            st.markdown(md(s["last_rejected"]["feedback"]))

    with tabs[2]:
        hist = s.get("historial", [])
        if hist:
            st.markdown("##### Revisiones del Supervisor")
            for h in reversed(hist):
                ok = h["veredicto"] == "aprobar"
                st.markdown(f"{'✅' if ok else '❌'} **Intento {h['intento']} · {'aprobado' if ok else 'rechazado'} "
                            f"({h['puntuacion']}/10)** · {h['fecha']}  \n{md(h['feedback'])}")
        if s.get("busquedas"):
            st.markdown("##### Búsquedas web que hizo")
            st.markdown("\n".join(f"- {md(q)}" for q in s["busquedas"]))
        tag = f"[{d['nombre']}]"
        entries = [e for e in P.get("log", []) if tag in e["msg"]]
        st.markdown("##### Registro")
        if entries:
            for e in reversed(entries[-25:]):
                st.caption(f"`{e['t']}` **{e['tag']}** · {md(e['msg'].replace(tag, '').strip())}")
        else:
            st.caption("Sin actividad todavía.")

    with tabs[3]:
        st.markdown(f"**En pocas palabras:** {resumen(d)}")
        st.markdown("**Su tarea**")
        st.markdown(md(d["tarea"]))
        st.markdown("**Qué comprueba el Supervisor**")
        st.markdown("\n".join(f"- {c}" for c in d.get("criterios", [])))
        if d.get("guia"):
            with st.expander("Guía metodológica que sigue", icon=":material/menu_book:"):
                st.markdown(md(d["guia"]))
        ls = memoria.get(d["id"], [])
        if ls:
            with st.expander(f"Lecciones aprendidas que aplica ({len(ls)})", icon=":material/school:"):
                st.markdown("\n".join(f"- {md(l['texto'])}" for l in ls[-12:]))

    if s["status"] == "blocked":
        with st.form(f"block_{d['id']}", border=True):
            note = st.text_area("Orientación para desbloquear", placeholder="Qué datos, enfoque o supuestos quieres que use…")
            if st.form_submit_button("Reintentar con esta orientación", type="primary"):
                s.update(human_note=note.strip(), attempts=0, status="stale" if s["output"] else "pending")
                E.add_log(P, "CEO", f"Orientación a [{d['nombre']}]: {note.strip() or '(reintento)'}")
                save()
                request_run(idx)

    if s["output"] and s["status"] in ("approved", "hold", "stale", "blocked"):
        with st.expander("Rechazar y pedir que lo rehaga", icon=":material/undo:"):
            with st.form(f"fb_{d['id']}"):
                fb = st.text_area("Qué debe corregir o tener en cuenta",
                                  placeholder="Ej.: usa Ke con prima país; el EBITDA 2024 incluye 0,4 M€ no recurrentes…")
                lesson = st.checkbox("Guardar también como lección para futuras valoraciones", value=True)
                if st.form_submit_button("Rehacer con estas indicaciones", type="primary") and fb.strip():
                    s.update(human_feedback=fb.strip(), attempts=0, status="stale",
                             last_rejected={"feedback": "(CEO) " + fb.strip(), "output": s["output"][:6000]})
                    if lesson:
                        E.add_lesson(memoria, d["id"], fb.strip(), "CEO", P["nombre"])
                    E.invalidate_from(P, customs, idx + 1)
                    E.add_log(P, "CEO", f"Rechazado [{d['nombre']}]: {fb.strip()}")
                    save()
                    request_run(idx)

    with st.expander("Editar el resultado a mano", icon=":material/edit:"):
        with st.form(f"ed_{d['id']}"):
            txt = st.text_area("Output (markdown)", s["output"], height=400)
            st.caption("Al guardar queda aprobado y los especialistas posteriores quedan desactualizados.")
            if st.form_submit_button("Guardar y aprobar"):
                s.update(output=txt, status="approved", sup_feedback="Editado a mano por el CEO.", sup_verdict="aprobar",
                         score=None, attempts=0, last_rejected=None, error="")
                E.invalidate_from(P, customs, idx + 1)
                E.add_log(P, "CEO", f"Output de [{d['nombre']}] editado a mano.")
                save()
                st.rerun()


# ─────────────────────────── información ───────────────────────────

def after_new_info(doc: dict) -> None:
    if not ctx:
        return
    try:
        r = E.route_info(ctx, P, doc)
    except E.MapsError as e:
        flash("warning", f"No se pudo analizar a quién afecta la información: {e}")
        return
    if r:
        ss.route = {**r, "cid": P["id"]}


def add_yahoo(p: dict, ticker: str, comps: list[str]) -> dict:
    """Añade a la empresa los datos de Yahoo Finance del ticker y de los comparables. Devuelve el último documento."""
    doc = None
    if ticker.strip():
        titulo, texto = market.company(ticker, p.get("tipo") == "financiera")
        doc = E.add_info(None, p, titulo, texto, "yahoo")
    if comps:
        titulo, texto = market.comparables(comps)
        doc = E.add_info(None, p, titulo, texto, "yahoo")
    return doc


def run_research(box, kind: str, query: str | None) -> None:
    if not ctx:
        flash("error", "Añade tu API key en la barra lateral para investigar en la web.")
        return
    if kind == "inicial":
        encargo, titulo = E.encargo_inicial(P), f"Investigación web inicial ({E.today()})"
    elif kind == "faltan":
        faltan = E.missing_by_agent(P, customs)
        encargo = "Datos que han pedido los especialistas:\n" + "\n\n".join(f"{n}:\n{t}" for n, t in faltan)
        titulo = f"Investigación web: datos que faltaban ({E.today()})"
    else:
        encargo, titulo = query, f"Investigación web: {query[:60]}"
    with box.status("🔎 El investigador está buscando en la web…", expanded=True) as stt:
        ph_s, ph = st.empty(), st.empty()
        last = [0.0]

        def on_text(t):
            if time.time() - last[0] > 0.3:
                ph.markdown(md(t))
                last[0] = time.time()

        try:
            doc = E.research(ctx, P, encargo, titulo, on_text=on_text,
                             on_search=lambda n: ph_s.caption(f"Búsquedas realizadas: {n}"))
        except E.MapsError as e:
            stt.update(label="La investigación ha fallado", state="error")
            flash("error", str(e))
            save()
            st.rerun()
        stt.update(label=f"Investigación terminada: {len(doc['fuentes'])} fuentes", state="complete", expanded=False)
    save()
    after_new_info(doc)
    save()
    flash("success", f"Añadido «{titulo}».")
    st.rerun()


def page_info() -> None:
    route_banner()
    box = st.container()
    if "research_req" in ss:
        kind, query = ss.pop("research_req")
        run_research(box, kind, query)
        return
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("#### 📈 Yahoo Finance (gratis)")
            st.caption("Cotización, múltiplos, consenso de analistas y cuentas anuales de los últimos 4 años. No gasta API.")
            with st.form("yahoo_form"):
                c1, c2 = st.columns([1, 2])
                tk = c1.text_input("Ticker", P.get("ticker", ""), placeholder="ITX.MC")
                comps = c2.text_input("Comparables (opcional, separados por comas)", placeholder="HM-B.ST, GAP, ABF.L")
                go_y = st.form_submit_button("Descargar datos")
            if go_y:
                if not tk.strip() and not comps.strip():
                    st.warning("Escribe un ticker o algún comparable.")
                else:
                    try:
                        with st.spinner("Descargando de Yahoo Finance…"):
                            doc = add_yahoo(P, tk, [c for c in comps.split(",") if c.strip()])
                        save()
                        after_new_info(doc)
                        save()
                        flash("success", "Datos de Yahoo Finance añadidos.")
                        st.rerun()
                    except E.MapsError as e:
                        save()
                        st.error(str(e))

        with st.container(border=True):
            st.markdown("#### 🔎 Investigación web")
            st.caption("Claude busca datos públicos (resultados, cotización, comparables, transacciones, tipos) y los guarda con sus fuentes.")
            faltan = E.missing_by_agent(P, customs)
            c1, c2 = st.columns(2)
            if c1.button("Investigación inicial", use_container_width=True, disabled=not ctx):
                ss.research_req = ("inicial", None)
                st.rerun()
            if c2.button(f"Buscar los datos que faltan ({len(faltan)})", use_container_width=True, disabled=not ctx or not faltan):
                ss.research_req = ("faltan", None)
                st.rerun()
            with st.form("q_form", clear_on_submit=True):
                q = st.text_input("Búsqueda concreta", placeholder="Ej.: P/VC tangible y ROTE de los bancos españoles cotizados")
                if st.form_submit_button("Buscar", disabled=not ctx) and q.strip():
                    ss.research_req = ("libre", q.strip())
                    st.rerun()

        with st.container(border=True):
            st.markdown("#### ✍️ Aportar información a mano")
            st.caption("Pega o sube cuentas anuales, presentaciones, presupuestos, cotizaciones, condiciones de una oferta…")
            with st.form("info_form", clear_on_submit=True):
                titulo = st.text_input("Título", placeholder="Ej.: Presentación de resultados 2T 2026")
                texto = st.text_area("Contenido", height=180, placeholder="Pega aquí texto o tablas…")
                ups = st.file_uploader("O sube archivos", accept_multiple_files=True,
                                       type=["pdf", "xlsx", "xls", "xlsm", "ods", "csv", "tsv", "txt", "md", "json", "png", "jpg", "jpeg", "webp"])
                sent = st.form_submit_button("Añadir información", type="primary")
            if sent:
                added = None
                try:
                    with st.spinner("Leyendo y procesando…"):
                        for f in ups or []:
                            added = E.add_info(ctx, P, f.name.rsplit(".", 1)[0], read_upload(f.name, f.getvalue(), ctx), "archivo")
                            save()
                        if texto.strip():
                            added = E.add_info(ctx, P, titulo, texto, "manual")
                            save()
                        if added:
                            after_new_info(added)
                            save()
                except E.MapsError as e:
                    save()
                    st.error(str(e))
                    return
                if added:
                    flash("success", "Información añadida.")
                    st.rerun()
                st.warning("Pega algún contenido o sube un archivo.")

    with right:
        faltan = E.missing_by_agent(P, customs)
        with st.container(border=True):
            st.markdown(f"#### Datos que piden los especialistas ({len(faltan)})")
            if not faltan:
                st.caption("Cuando los especialistas trabajen, aquí aparecerán los datos que necesitan para afinar la valoración.")
            for n, t in faltan:
                st.markdown(f"**{n}**")
                st.markdown(md(t))
        st.markdown(f"#### Documentos ({len(P.get('info', []))})")
        if not P.get("info"):
            st.caption("Todavía no hay documentos.")
        for d in reversed(P.get("info", [])):
            icon = {"web": "🌐", "archivo": "📎", "yahoo": "📈"}.get(d.get("origen"), "✍️")
            with st.expander(f"{icon} {d['titulo']} · {d.get('fecha', '')}"):
                if d.get("resumen"):
                    st.caption("Extracto que usan los especialistas:")
                    st.markdown(md(d["resumen"]))
                    st.divider()
                st.markdown(md(d["texto"][:30000]))
                if d.get("fuentes"):
                    st.caption("Fuentes:")
                    for f in d["fuentes"]:
                        st.markdown(f"- [{f['titulo']}]({f['url']})")
                if st.button("Borrar documento", key=f"del_{d['id']}"):
                    P["info"] = [x for x in P["info"] if x["id"] != d["id"]]
                    E.add_log(P, "CEO", f"Documento borrado: «{d['titulo']}».")
                    save()
                    st.rerun()


# ─────────────────────────── informe ───────────────────────────

def football_chart(r: dict) -> go.Figure:
    ms = r["metodos"]
    fig = go.Figure(go.Bar(y=[m["metodo"] for m in ms], x=[m["max"] - m["min"] for m in ms], base=[m["min"] for m in ms],
                           orientation="h", marker_color="#2447D6", opacity=.85,
                           text=[f"{fmt(m['min'])} – {fmt(m['max'])}" for m in ms], textposition="outside",
                           hovertemplate="%{y}: %{base:.1f} – %{customdata:.1f}<extra></extra>", customdata=[m["max"] for m in ms]))
    fig.add_vrect(x0=r["final"]["min"], x1=r["final"]["max"], fillcolor="#0F7F58", opacity=.13, line_width=0,
                  annotation_text="Rango final", annotation_position="top left")
    fig.add_vline(x=r["final"]["central"], line_color="#0F7F58", line_width=2,
                  annotation_text=f"Central {fmt(r['final']['central'])}", annotation_position="bottom right")
    fig.update_layout(height=90 + 46 * len(ms), margin=dict(l=10, r=40, t=30, b=30), showlegend=False,
                      xaxis_title=f"Valor del equity ({r['unidad']} {r['moneda']})", yaxis=dict(autorange="reversed"))
    return fig


def page_report() -> None:
    r = P.get("resumen")
    chain_ = ch()
    with st.container(border=True):
        st.markdown("#### Football field")
        if r:
            c = st.columns(4)
            c[0].metric("Rango final", f"{fmt(r['final']['min'])} – {fmt(r['final']['max'])} {r['unidad']} {r['moneda']}")
            c[1].metric("Valor central", f"{fmt(r['final']['central'])} {r['unidad']}")
            pa = r.get("por_accion")
            if pa:
                c[2].metric("Por acción", f"{fmt(pa['min'])} – {fmt(pa['max'])} {r['moneda']}")
                if r.get("precio_actual"):
                    pot = (pa["central"] / r["precio_actual"] - 1) * 100
                    c[3].metric("Frente a la cotización", f"{fmt(r['precio_actual'])} {r['moneda']}", f"{pot:+.1f} % potencial")
            if r.get("frase"):
                st.markdown(md(r["frase"]))
            if r["metodos"]:
                st.plotly_chart(football_chart(r), use_container_width=True)
        elif E.agent(P, "sintesis")["status"] == "approved":
            if st.button("Extraer rango de la síntesis", disabled=not ctx):
                try:
                    E.extract_football(ctx, P)
                    save()
                except E.MapsError as e:
                    st.error(str(e))
                st.rerun()
        else:
            st.caption("El gráfico aparece cuando el Director de síntesis termina y el Supervisor lo aprueba.")

    done = [d for d in chain_ if E.agent(P, d["id"])["output"]]
    c1, _ = st.columns([1, 4])
    c1.download_button("⬇ Descargar informe (.md)", E.report_md(P, customs), file_name=f"Valoracion_{P['nombre'].replace(' ', '_')}.md",
                       mime="text/markdown", disabled=not done)
    if not done:
        st.caption("Documento Maestro vacío. Se llena a medida que el Supervisor aprueba outputs.")
    for d in done:
        s = E.agent(P, d["id"])
        st.markdown(f"### {d['nombre']}  \n{STATUS[s['status']][1]} {STATUS[s['status']][0]}")
        st.markdown(md(s["output"]))
        st.divider()


# ─────────────────────────── memoria ───────────────────────────

def page_memory() -> None:
    all_defs = CATALOG + [{**c, "grupo": "Personalizados"} for c in customs]
    left, right = st.columns([1.4, 1], gap="large")
    with left:
        total = sum(len(v) for v in memoria.values())
        st.markdown(f"#### Lecciones aprendidas ({total})")
        st.caption("Se crean cuando el Supervisor detecta un fallo generalizable o cuando rechazas un trabajo y marcas «Guardar como lección». "
                   "Cada especialista las lee antes de trabajar, en todas las empresas.")
        for d in all_defs:
            ls = memoria.get(d["id"], [])
            if not ls:
                continue
            with st.container(border=True):
                st.markdown(f"**{d['nombre']}** · {len(ls)}")
                for i, l in enumerate(ls):
                    c1, c2 = st.columns([12, 1])
                    c1.markdown(f"{md(l['texto'])}  \n:gray[{l.get('origen', '')} · {l.get('empresa', '')} · {l.get('fecha', '')}]")
                    if c2.button("✕", key=f"dl_{d['id']}_{i}", help="Borrar lección"):
                        ls.pop(i)
                        storage.save_memoria(memoria)
                        st.rerun()
    with right, st.form("add_lesson", clear_on_submit=True):
        st.markdown("#### Añadir lección a mano")
        aid = st.selectbox("Especialista", [d["id"] for d in all_defs], format_func=lambda i: E.def_of(i, customs)["nombre"])
        txt = st.text_area("Lección", placeholder="Ej.: En pymes españolas aplica prima de tamaño de 3-5 pp y descuento por iliquidez del 20-30 %.")
        if st.form_submit_button("Guardar lección") and txt.strip():
            E.add_lesson(memoria, aid, txt, "CEO (manual)", P["nombre"] if P else "")
            st.rerun()


# ─────────────────────────── configuración ───────────────────────────

def page_config() -> None:
    with st.form("cfg"):
        st.markdown("#### Empresa")
        data = company_fields(f"cf_{P['id']}_", P)
        if st.form_submit_button("Guardar cambios"):
            changed = any(str(P.get(k, "")) != str(data[k]) for k in data if k != "nombre")
            P.update(data)
            if changed:
                E.invalidate_from(P, customs, 0)
                E.add_log(P, "CEO", "Datos de la empresa modificados: cadena desactualizada.")
            save()
            flash("success", "Guardado." + (" La cadena está desactualizada: pulsa Continuar para rehacerla." if changed else ""))
            st.rerun()

    with st.container(border=True):
        st.markdown("#### Ejecución")
        c1, c2 = st.columns(2)
        rev = c1.toggle("Pedir mi visto bueno tras cada especialista", P.get("revision", False))
        web = c2.toggle("Los especialistas pueden buscar en la web", P.get("web_especialistas", False))
        c1, c2 = st.columns(2)
        wu = c1.slider("Búsquedas máximas por especialista", 1, 10, int(P.get("web_uses", 2)), disabled=not web)
        wr = c2.slider("Búsquedas máximas por investigación", 5, 30, int(P.get("web_uses_research", 5)))
        if (rev, web, wu, wr) != (P.get("revision", False), P.get("web_especialistas", False), P.get("web_uses", 2), P.get("web_uses_research", 5)):
            P.update(revision=rev, web_especialistas=web, web_uses=wu, web_uses_research=wr)
            save()
        st.caption("Coste orientativo de una cadena completa: ~0,3-0,8 $ con Haiku 4.5, ~1,5-4 $ con Sonnet 5 y 3-10 $ con Opus 5. "
                   "Cada búsqueda web cuesta 0,01 $ y además añade texto que se cobra como entrada.")

    with st.container(border=True):
        st.markdown(f"#### Módulos de la cadena ({len(ch())} activos)")
        cols = st.columns(len(PRESETS))
        for col, (k, pr) in zip(cols, PRESETS.items()):
            if col.button(pr["label"], use_container_width=True, key=f"pre_{k}"):
                if pr["tipo"] == "financiera":
                    P["tipo"] = "financiera"
                apply_mods(pr["mods"])
                st.rerun()
        all_defs = CATALOG + [{**c, "grupo": "Personalizados"} for c in customs]
        with st.form("mods"):
            sel = []
            for g in GROUPS:
                defs = [d for d in all_defs if d["grupo"] == g]
                if not defs:
                    continue
                st.markdown(f"**{g}**")
                gc = st.columns(3)
                for i, d in enumerate(defs):
                    on = gc[i % 3].checkbox(d["nombre"], d.get("fixed") or d["id"] in P.get("modulos", []), disabled=bool(d.get("fixed")),
                                            key=f"mod_{P['id']}_{P.get('mods_v', 0)}_{d['id']}", help=f"{resumen(d)}\n\n{d['tarea']}")
                    if on and not d.get("fixed"):
                        sel.append(d["id"])
            st.caption("Al añadir un módulo, los especialistas posteriores ya aprobados pasan a «Desactualizado» para integrar su trabajo.")
            if st.form_submit_button("Aplicar módulos"):
                apply_mods(sel)
                st.rerun()

    with st.container(border=True), st.form("custom", clear_on_submit=True):
        st.markdown("#### Crear especialista personalizado")
        st.caption("Queda disponible para todas las empresas. Ej.: «Experto en startups SaaS», «Analista inmobiliario», «Asesor fiscal de la operación».")
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre")
        despues = c2.selectbox("Va después de", [c["id"] for c in CATALOG if c["id"] != "sintesis"],
                               index=[c["id"] for c in CATALOG].index("sensibilidad"), format_func=lambda i: E.def_of(i, customs)["nombre"])
        tarea = st.text_area("Tarea", placeholder="Qué debe analizar y qué debe entregar…")
        crit = st.text_area("Criterios del Supervisor (uno por línea)")
        if st.form_submit_button("Crear y activar en esta empresa"):
            if nombre.strip() and tarea.strip():
                c = {"id": storage.new_id("c_"), "nombre": nombre.strip(), "tarea": tarea.strip(), "despues": despues,
                     "criterios": [x.strip() for x in crit.splitlines() if x.strip()] or ["Cumple la tarea con cálculos visibles", "Coherente con el Testigo"]}
                customs.append(c)
                storage.save_customs(customs)
                apply_mods(P.get("modulos", []) + [c["id"]])
                E.add_log(P, "CEO", f"Especialista personalizado creado: {c['nombre']}.")
                save()
                st.rerun()
            st.warning("El especialista necesita nombre y tarea.")
    if customs:
        with st.expander(f"Especialistas personalizados ({len(customs)})"):
            for c in customs:
                c1, c2 = st.columns([6, 1])
                c1.markdown(f"**{c['nombre']}** — después de {E.def_of(c['despues'], customs)['nombre']}")
                if c2.button("Borrar", key=f"dc_{c['id']}"):
                    customs[:] = [x for x in customs if x["id"] != c["id"]]
                    storage.save_customs(customs)
                    apply_mods([m for m in P.get("modulos", []) if m != c["id"]])
                    st.rerun()

    with st.container(border=True):
        st.markdown("#### Zona peligrosa")
        c1, c2 = st.columns(2)
        if c1.button("Reiniciar toda la cadena"):
            P.update(agentes={}, resumen=None, estado="setup")
            E.add_log(P, "CEO", "Cadena reiniciada.")
            save()
            st.rerun()
        conf = c2.checkbox(f"Confirmo que quiero borrar «{P['nombre']}» y toda su información")
        if c2.button("Borrar empresa", disabled=not conf):
            storage.delete_company(P["id"])
            ss.goto = "Cadena"
            st.rerun()


# ─────────────────────────── enrutado ───────────────────────────

if ss.flash:
    kind, msg = ss.flash
    getattr(st, kind)(msg)
    ss.flash = None

if ss.page == "nueva" or not P:
    page_new()
else:
    if "goto" in ss:
        ss.nav_radio = ss.pop("goto")
    st.title(P["nombre"], anchor=False)
    st.caption(" · ".join(x for x in [TIPOS.get(P.get("tipo", "empresa")), P.get("sector"), P.get("ticker"), P.get("proposito")] if x))
    st.radio("Sección", NAV, key="nav_radio", horizontal=True, label_visibility="collapsed")
    {"Cadena": page_chain, "Información": page_info, "Informe": page_report,
     "Memoria": page_memory, "Configuración": page_config}[ss.nav_radio]()
