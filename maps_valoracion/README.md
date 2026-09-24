# MAPS Valoración

Sistema multi-agente para valorar empresas con Claude. Tú haces de **CEO**: defines la empresa y aportas información. Una cadena de **especialistas** hace el trabajo y cada uno le pasa el suyo (el "Testigo") al siguiente. Un **Supervisor** revisa cada entrega y puede pedir que se rehaga una vez; si vuelve a fallar, te pide que intervengas.

## Puesta en marcha

```powershell
cd C:\Users\pelay\maps_valoracion
.\.venv\Scripts\streamlit run app.py
```

Necesitas una API key de Anthropic, que se crea en console.anthropic.com. Puedes darla de tres formas:

- **Variable de entorno:** `setx ANTHROPIC_API_KEY "sk-ant-..."`. Después abre una terminal nueva.
- **Archivo local:** `.streamlit/secrets.toml` con la línea `ANTHROPIC_API_KEY = "sk-ant-..."`.
- **En la app:** pégala en la barra lateral. Solo dura mientras la sesión esté abierta.

Para instalarlo en otro equipo:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

## Cómo se usa

1. **Crea la empresa.** Elige una plantilla: Pyme no cotizada, Cotizada, M&A venta/compra, Banca / seguros o Completa. Si dejas marcada "Investigar en la web", Claude busca los datos públicos al crearla (hasta 5 búsquedas).
2. **Pestaña Información.** Aquí entra la información de tres maneras:
   - **Investigación inicial:** Claude busca resultados, cotización, comparables, transacciones y tipos de interés, y guarda cada dato con su fuente.
   - **Buscar los datos que faltan:** busca lo que los especialistas han pedido en sus secciones "Datos que faltan".
   - **A mano:** pegas texto o subes archivos (PDF, incluidos los escaneados, Excel, CSV o imágenes).

   Cada vez que añades información, la app detecta a qué especialistas afecta y te propone rehacer la cadena desde el primero de ellos.
3. **Pestaña Cadena.** Pulsa **Ejecutar cadena** para ver trabajar a cada especialista en directo. Sobre cualquier especialista puedes rechazar con indicaciones, editar el output a mano o ejecutar la cadena desde ese punto.
4. **Pestaña Informe.** Muestra el football field, el rango de valor, el valor por acción y el potencial frente a la cotización. También puedes descargar el informe completo en `.md`.
5. **Pestaña Memoria.** Guarda las lecciones que ha aprendido cada especialista, tanto las del Supervisor como las tuyas. Se aplican en todas las valoraciones siguientes.

## Estructura

| Archivo | Contenido |
|---|---|
| `app.py` | Interfaz de Streamlit |
| `maps/catalog.py` | Los 19 especialistas (tarea y criterios del Supervisor), las plantillas y los precios |
| `maps/engine.py` | Prompts, llamadas a Claude con búsqueda web, el Supervisor y el bucle de la cadena |
| `maps/files.py` | Lectura de PDF, Excel, CSV e imágenes |
| `maps/storage.py` | Guardado en JSON dentro de `data/` (empresas, memoria y especialistas personalizados) |

## Detalles técnicos

- **Modelo:** Claude Haiku 4.5 por defecto, que es el más barato (1 $/5 $ por millón de tokens de entrada/salida) y no usa razonamiento. En la barra lateral puedes subir a Sonnet 5 o a Opus 5, que tienen razonamiento adaptativo y esfuerzo configurable.
- **Búsqueda web:** usa la herramienta `web_search` del servidor de Anthropic. Cada búsqueda cuesta 0,01 $ y además añade texto que se cobra como entrada. Por defecto los especialistas **no** buscan; puedes activarlo en Configuración.
- **Fallbacks:** con Sonnet 5 y Opus 5 el parámetro `fallbacks="default"` está activado. Si Claude rechaza una petición por sus filtros de seguridad, la API la repite automáticamente con otro modelo.
- **Caché de prompts:** el bloque con los datos de la empresa y la información es igual para todos los especialistas, así que se guarda en caché y abarata cada paso de la cadena.
- **Coste orientativo por cadena:** ~0,3-0,8 $ con Haiku 4.5, ~1,5-4 $ con Sonnet 5 y 3-10 $ con Opus 5. El coste real acumulado de cada empresa aparece en la barra lateral.
