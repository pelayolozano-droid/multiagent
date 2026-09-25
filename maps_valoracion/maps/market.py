"""Datos de mercado gratuitos desde Yahoo Finance (yfinance), sin pasar por Claude."""
from __future__ import annotations

import math

import yfinance as yf

from .engine import MapsError

# (etiqueta, filas candidatas de yfinance). Se usa la primera que exista: bancos y empresas usan filas distintas.
INCOME = [
    ("Ventas / ingresos totales", ["Total Revenue", "Operating Revenue"]),
    ("Margen de intereses", ["Net Interest Income"]),
    ("EBITDA", ["EBITDA", "Normalized EBITDA"]),
    ("EBIT", ["EBIT", "Operating Income"]),
    ("Gasto por intereses", ["Interest Expense"]),
    ("Impuestos", ["Tax Provision"]),
    ("Beneficio neto atribuido", ["Net Income Common Stockholders", "Net Income"]),
    ("BPA diluido", ["Diluted EPS"]),
]
BALANCE = [
    ("Activo total", ["Total Assets"]),
    ("Patrimonio neto (dominante)", ["Stockholders Equity", "Common Stock Equity"]),
    ("Valor contable tangible", ["Tangible Book Value"]),
    ("Deuda financiera total (incl. arrendamientos)", ["Total Debt"]),
    ("Arrendamientos (IFRS 16)", ["Capital Lease Obligations"]),
    ("Caja y equivalentes", ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]),
    ("Deuda neta", ["Net Debt"]),
    ("Capital circulante", ["Working Capital"]),
    ("Intereses minoritarios", ["Minority Interest"]),
    ("Acciones en circulación", ["Ordinary Shares Number"]),
]
CASHFLOW = [
    ("Flujo de caja operativo", ["Operating Cash Flow"]),
    ("Capex", ["Capital Expenditure"]),
    ("Flujo de caja libre", ["Free Cash Flow"]),
    ("Variación del capital circulante", ["Change In Working Capital"]),
    ("Dividendos pagados", ["Cash Dividends Paid"]),
    ("Recompra de acciones", ["Repurchase Of Capital Stock"]),
]
PER_SHARE = {"BPA diluido"}
# En bancos el EBITDA, la deuda neta y el flujo de caja libre no tienen sentido; en empresas, el margen de intereses.
SOLO_FINANCIERA = {"Margen de intereses", "Valor contable tangible"}
SOLO_EMPRESA = {"EBITDA", "Deuda neta", "Capital circulante", "Arrendamientos (IFRS 16)"}
COUNT = {"Acciones en circulación"}


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _fmt(v, dec: int = 1) -> str:
    f = _num(v)
    return "—" if f is None else f"{f:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v) -> str:
    f = _num(v)
    return "—" if f is None else _fmt(f * 100, 1) + " %"


def _mill(v) -> str:
    f = _num(v)
    return "—" if f is None else _fmt(f / 1e6, 1)


def _statement(df, rows: list[tuple[str, list[str]]], title: str, cur: str, financiera: bool) -> str:
    if df is None or df.empty:
        return ""
    cols = list(df.columns)[:4]
    head = f"### {title} (millones de {cur}, salvo indicación)\n\n| Partida | " + " | ".join(
        getattr(c, "strftime", lambda f: str(c))("%Y-%m") for c in cols) + " |\n|---|" + "---:|" * len(cols)
    lines = []
    for label, cands in rows:
        if label in (SOLO_EMPRESA if financiera else SOLO_FINANCIERA - {"Valor contable tangible"}):
            continue
        name = next((c for c in cands if c in df.index), None)
        if not name:
            continue
        vals = df.loc[name, cols]
        if all(_num(v) is None for v in vals):
            continue
        if label in PER_SHARE:
            cells, label = [_fmt(v, 2) for v in vals], f"{label} ({cur}/acción)"
        elif label in COUNT:
            cells, label = [_mill(v) for v in vals], f"{label} (millones)"
        else:
            cells = [_mill(v) for v in vals]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return head + "\n" + "\n".join(lines) if lines else ""


def _info(t: yf.Ticker) -> dict:
    try:
        i = t.info or {}
    except Exception as e:  # yfinance lanza errores variados (red, límite de peticiones, ticker inexistente)
        raise MapsError(f"Yahoo Finance no ha respondido para {t.ticker}: {e}") from e
    if not (i.get("longName") or i.get("shortName")) or not (i.get("currentPrice") or i.get("regularMarketPrice")):
        raise MapsError(f"Yahoo Finance no tiene datos de «{t.ticker}». Revisa el ticker (p. ej. ITX.MC, SAN.MC, AAPL).")
    return i


def company(ticker: str, financiera: bool = False) -> tuple[str, str]:
    """Devuelve (título, markdown) con cotización, múltiplos, consenso y estados financieros anuales."""
    t = yf.Ticker(ticker.strip().upper())
    i = _info(t)
    cur = i.get("financialCurrency") or i.get("currency") or ""
    qcur = i.get("currency") or cur
    price = i.get("currentPrice") or i.get("regularMarketPrice")
    name = i.get("longName") or i.get("shortName")
    rows = [
        ("Precio actual", f"{_fmt(price, 2)} {qcur}"),
        ("Rango 52 semanas", f"{_fmt(i.get('fiftyTwoWeekLow'), 2)} – {_fmt(i.get('fiftyTwoWeekHigh'), 2)} {qcur}"),
        ("Acciones en circulación", f"{_mill(i.get('sharesOutstanding'))} millones"),
        ("Capitalización", f"{_mill(i.get('marketCap'))} M {qcur}"),
        ("Valor de empresa (EV)", f"{_mill(i.get('enterpriseValue'))} M {qcur}"),
        ("Deuda total / caja (último balance)", f"{_mill(i.get('totalDebt'))} / {_mill(i.get('totalCash'))} M {cur}"),
        ("Ventas / EBITDA últimos 12 meses", f"{_mill(i.get('totalRevenue'))} / {_mill(i.get('ebitda'))} M {cur}"),
        ("Margen EBITDA / operativo / neto", f"{_pct(i.get('ebitdaMargins'))} / {_pct(i.get('operatingMargins'))} / {_pct(i.get('profitMargins'))}"),
        ("Crecimiento de ventas (interanual)", _pct(i.get("revenueGrowth"))),
        ("ROE / ROA", f"{_pct(i.get('returnOnEquity'))} / {_pct(i.get('returnOnAssets'))}"),
        ("EV/EBITDA · EV/Ventas", f"{_fmt(i.get('enterpriseToEbitda'))}x · {_fmt(i.get('enterpriseToRevenue'))}x"),
        ("PER histórico · PER estimado", f"{_fmt(i.get('trailingPE'))}x · {_fmt(i.get('forwardPE'))}x"),
        ("Precio / valor contable", f"{_fmt(i.get('priceToBook'), 2)}x"),
        ("Beta (Yahoo, 5 años mensual)", _fmt(i.get("beta"), 2)),
        ("Dividendo por acción · rentabilidad · payout", f"{_fmt(i.get('dividendRate'), 2)} {qcur} · {_fmt(i.get('dividendYield'), 2)} % · {_pct(i.get('payoutRatio'))}"),
        ("Consenso: precio objetivo medio (mín–máx)", f"{_fmt(i.get('targetMeanPrice'), 2)} ({_fmt(i.get('targetLowPrice'), 2)}–{_fmt(i.get('targetHighPrice'), 2)}) {qcur}"),
        ("Consenso: recomendación · nº analistas", f"{i.get('recommendationKey') or '—'} · {i.get('numberOfAnalystOpinions') or '—'}"),
    ]
    md = (f"**{name}** ({t.ticker}) · {i.get('sector') or ''} / {i.get('industry') or ''} · {i.get('country') or ''}\n\n"
          f"Fuente: Yahoo Finance (https://finance.yahoo.com/quote/{t.ticker}). Datos descargados automáticamente; "
          f"los múltiplos de Yahoo usan su propia definición de EV y EBITDA: contrástalos con los estados financieros.\n\n"
          "### Mercado y múltiplos\n\n| Dato | Valor |\n|---|---|\n" + "\n".join(f"| {a} | {b} |" for a, b in rows))
    statements = [(lambda: t.income_stmt, INCOME, "Cuenta de resultados anual"), (lambda: t.balance_sheet, BALANCE, "Balance anual")]
    if not financiera:
        statements.append((lambda: t.cashflow, CASHFLOW, "Flujos de caja anuales"))
    for df_get, rows_, title in statements:
        try:
            block = _statement(df_get(), rows_, title, cur, financiera)
        except Exception:
            block = ""
        if block:
            md += "\n\n" + block
    return f"Yahoo Finance: {name} ({t.ticker})", md


# Bolsas principales primero; las cotizaciones secundarias (OTC, bolsas regionales alemanas, CDR…) al final.
_BOLSAS_PRINCIPALES = ("Madrid", "NYSE", "NASDAQ", "Nasdaq", "Paris", "XETRA", "London", "Milan", "Amsterdam", "Lisbon",
                       "Brussels", "Swiss", "Toronto", "Tokyo", "Hong Kong", "Stockholm", "Copenhagen", "Oslo", "Helsinki")
_SECUNDARIO = ("CDR", "SPONSORED", "ADR", "FUTURES")
# Empresas que la búsqueda de Yahoo no devuelve en su bolsa principal.
_ALIAS = {"inditex": "ITX.MC", "zara": "ITX.MC"}
PAISES = {"Spain": "España", "United States": "Estados Unidos", "France": "Francia", "Germany": "Alemania",
          "United Kingdom": "Reino Unido", "Italy": "Italia", "Netherlands": "Países Bajos", "Portugal": "Portugal",
          "Switzerland": "Suiza", "Mexico": "México", "Brazil": "Brasil", "Japan": "Japón", "China": "China"}


def search(query: str, n: int = 6) -> list[dict]:
    """Empresas cotizadas que coinciden con el nombre, con la bolsa principal primero."""
    q = query.strip()
    if not q:
        return []
    try:
        quotes = yf.Search(q, max_results=20, news_count=0).quotes
    except Exception as e:
        raise MapsError(f"No se pudo buscar en Yahoo Finance: {e}") from e
    res = [{"symbol": x["symbol"], "nombre": x.get("longname") or x.get("shortname") or x["symbol"], "bolsa": x.get("exchDisp", ""),
            "corto": (x.get("shortname") or "").upper()}
           for x in quotes if x.get("quoteType") == "EQUITY" and x.get("symbol")]
    alias = _ALIAS.get(q.lower())
    if alias and all(r["symbol"] != alias for r in res):
        res.insert(0, {"symbol": alias, "nombre": q.title(), "bolsa": "Madrid"})

    def clave(r):  # dos primeras palabras del nombre, para reconocer la misma empresa en varias bolsas
        return " ".join("".join(ch for ch in r["nombre"].upper() if ch.isalnum() or ch == " ").split()[:2])

    def principal(r):
        nombres = r["nombre"].upper() + " " + r.get("corto", "")
        return any(b in r["bolsa"] for b in _BOLSAS_PRINCIPALES) and not any(s in nombres for s in _SECUNDARIO)

    us = ("NYSE", "NASDAQ", "Nasdaq")
    locales = {clave(r) for r in res if principal(r) and not any(b in r["bolsa"] for b in us)}

    def score(r):
        # Una empresa extranjera cotiza en EE. UU. como ADR: su bolsa local va primero.
        adr = any(b in r["bolsa"] for b in us) and clave(r) in locales
        parecido = r["symbol"].split(".")[0].startswith(q[:4].upper())
        return (0 if principal(r) else 1, 1 if adr else 0, 0 if parecido else 1)
    return sorted(res, key=score)[:n]


def profile(ticker: str) -> dict:
    """Ficha básica para rellenar la empresa automáticamente."""
    t = yf.Ticker(ticker.strip().upper())
    i = _info(t)
    industria = i.get("industry") or ""
    return {"symbol": t.ticker, "nombre": i.get("longName") or i.get("shortName"), "sector": i.get("sector") or "",
            "industria": industria, "industry_key": i.get("industryKey") or "",
            "pais": PAISES.get(i.get("country") or "", i.get("country") or ""),
            "moneda": i.get("financialCurrency") or i.get("currency") or "", "moneda_cotiz": i.get("currency") or "",
            "precio": i.get("currentPrice") or i.get("regularMarketPrice"), "capitalizacion": i.get("marketCap"),
            "financiera": industria.startswith(("Banks", "Insurance")),
            "descripcion": (i.get("longBusinessSummary") or "")[:600]}


def peers(industry_key: str, exclude: str, n: int = 5) -> list[str]:
    """Principales empresas cotizadas de la misma industria según Yahoo (sirven de comparables orientativos)."""
    if not industry_key:
        return []
    try:
        df = yf.Industry(industry_key).top_companies
    except Exception:
        return []
    if df is None or df.empty:
        return []
    return [s for s in df.index.tolist() if s and s.upper() != exclude.upper()][:n]


def comparables(tickers: list[str]) -> tuple[str, str]:
    """Tabla de múltiplos de un grupo de comparables cotizados."""
    lines, fails = [], []
    for tk in tickers:
        tk = tk.strip().upper()
        if not tk:
            continue
        try:
            i = _info(yf.Ticker(tk))
        except MapsError:
            fails.append(tk)
            continue
        lines.append(f"| {i.get('shortName') or i.get('longName')} ({tk}) | {i.get('currency') or ''} | {_mill(i.get('marketCap'))} | "
                     f"{_mill(i.get('enterpriseValue'))} | {_fmt(i.get('enterpriseToEbitda'))} | {_fmt(i.get('enterpriseToRevenue'))} | "
                     f"{_fmt(i.get('trailingPE'))} | {_fmt(i.get('forwardPE'))} | {_fmt(i.get('priceToBook'), 2)} | "
                     f"{_pct(i.get('ebitdaMargins'))} | {_pct(i.get('revenueGrowth'))} | {_pct(i.get('returnOnEquity'))} | {_fmt(i.get('beta'), 2)} |")
    if not lines:
        raise MapsError("Yahoo Finance no ha devuelto datos de ningún comparable. Revisa los tickers.")
    md = ("Fuente: Yahoo Finance. Capitalización y EV en millones de la moneda de cotización de cada compañía.\n\n"
          "| Compañía | Moneda | Capitalización | EV | EV/EBITDA | EV/Ventas | PER | PER est. | P/VC | Margen EBITDA | Crec. ventas | ROE | Beta |\n"
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n" + "\n".join(lines))
    if fails:
        md += f"\n\nSin datos en Yahoo: {', '.join(fails)}."
    return f"Yahoo Finance: comparables ({len(lines)})", md
