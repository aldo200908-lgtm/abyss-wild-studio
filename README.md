# ABYSS WILD — Shorts Studio v1.0

Interfaz de una sola página HTML y renderizado remoto con GitHub Actions, Python, Remotion y FFmpeg. No se necesita PC ni Termux y **no publica en YouTube**. El tema de prueba es **Titanoboa**.

## Qué hace

1. Investiga cualquier idea enciclopédica: convierte el tema o pregunta del usuario en búsquedas para Wikipedia en español e inglés, filtra fuentes relacionadas y recupera imágenes de Wikimedia Commons.
2. Pide un guion JSON y una revisión factual a Gemini Flash-Lite por API gratuita.
3. Rechaza guiones sin citas que respalden todas sus escenas (la validación por IA no sustituye revisión humana).
4. Narra con Azure AI Speech mediante una voz neural nativa `es-*` validada en `config.json`, sin fallback oculto. Whisper `small` verifica al menos 92 % de coincidencia y FFmpeg mide LUFS y pico estimado.
5. Busca imágenes CC0, dominio público, CC BY y CC BY-SA, y, opcionalmente, clips de Pexels. Usa visión Gemini para descartar coincidencias falsas. Si no hay coincidencia, usa gráficos tipográficos originales.
6. Genera 1080 × 1920 / 30 fps con Remotion, subtítulos destacados, escenas breves y barra comparativa si hay longitud demostrada.
7. Crea música ambiente original y efectos procedurales (sin música de terceros), mezcla en FFmpeg y verifica dimensiones, duración, volumen, tiempo de cortes y unicidad de recursos.
8. Publica **solo archivos descargables en una GitHub Release pública**. Nunca sube nada a YouTube.


## Temas personalizados: no solo Titanoboa

ABYSS WILD **no está limitado a un animal o a videos anteriores**: puedes introducir nombres, preguntas, fenómenos científicos, hechos históricos, tecnología o una idea nueva. Ejemplos de temas: `¿Por qué brilla el mar de noche?`, `Cómo funciona un agujero negro`, `La Antártida`, `Historia de los teléfonos móviles` y `Titanoboa`.

Desde GitHub Actions o la interfaz de Pages puedes cambiar `topic` cada vez, sin modificar código. El sistema convierte la solicitud en búsquedas en Wikipedia en **español e inglés**, pide a Gemini que escoja artículos cuyo asunto sea realmente relevante, extrae fragmentos citables y exige que el guion explique el tema, no un asunto tangencial. Las escenas se auditan tanto por respaldo factual como por enfoque editorial antes de producir el video. Las búsquedas no convierten el conocimiento de Gemini en fuente: cada afirmación debe apoyarse en un fragmento recuperado.

**Limitación importante:** con solo Wikipedia/Wikimedia no se puede garantizar cubrir literalmente cualquier tema, noticia de hoy, dato privado, obra ficticia propia ni asuntos sin entradas enciclopédicas pertinentes. Si falta evidencia suficiente, el proceso se detiene y no fabrica hechos. Wikipedia es una referencia introductoria, no una investigación independiente ni garantía de exactitud. Revisa guion, imágenes y créditos antes de publicar.

La primera pantalla deja «Titanoboa» como demostración, pero se puede reemplazar por cualquier otro texto. Para títulos de preguntas no se exige una coincidencia literal con el nombre de una página; por ejemplo, «¿Por qué brilla el mar de noche?» puede estudiarse consultando «Bioluminiscencia».

## Preparación en Android, paso por paso

1. Descarga el ZIP proporcionado, descomprímelo con la app **Archivos** y conserva las carpetas exactamente como aparecen. No subas el ZIP sin extraer: GitHub Actions necesita ver los archivos individuales.
2. En la app de GitHub o Chrome, crea un repositorio **público** llamado `abyss-wild-studio`, con la rama principal **main**. Ten presente que un repositorio público mostrará su código y las Releases con videos.
3. Desde **Chrome con Sitio para ordenadores**, entra en `https://github.dev/TU_USUARIO/abyss-wild-studio`. Crea/sube cada archivo manteniendo los nombres y rutas de la estructura. Si github.dev no deja subir carpetas desde Android, usa GitHub web → **Add file → Create new file**, escribe el nombre con su ruta (`.github/workflows/generate.yml`, `render/src/index.jsx`, etc.), pega el contenido de cada archivo y confirma. Es imprescindible conservar `.github/workflows/` y `render/`.
4. Asegúrate de haber subido `index.html`, `pipeline.py`, `budget.py`, `requirements.txt`, `render/package.json`, `render/render.mjs`, `render/src/index.jsx`, `.github/workflows/generate.yml`, `.gitignore` y `README.md`. No subas carpetas `node_modules`, `work`, `dist` ni archivos de claves. El directorio `render/public/media` se creará durante la ejecución.
5. Abre `https://aistudio.google.com/apikey` y crea una **API key del nivel gratuito** de Gemini (sin activar facturación de pago). En GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**, crea `GEMINI_API_KEY` con ese valor.
6. Opcional: solicita una clave en `https://www.pexels.com/api/`. Crea `PEXELS_API_KEY` como otro Secret. Si no lo haces, el pipeline usará Commons y gráficos propios. Pexels emplea una licencia gratuita propia, **no una licencia Creative Commons**.
7. En **Settings → Secrets and variables → Actions → Variables**, crea `MONTHLY_LIMIT_PEN` con `20`; opcionales `GEMINI_MODEL` con `gemini-3.5-flash-lite`, `USD_PEN` con `3.50` y `RUNNER_PRICE_USD_PER_MIN` con `0.006` para el estimador conservador de repositorios privados.
8. En **Settings → Actions → General**, permite las Actions necesarias. En **Workflow permissions**, selecciona **Read and write permissions** para que GitHub Actions pueda crear la Release con `GITHUB_TOKEN` (el workflow también solicita `contents: write`). Si existe una política organizacional que impida esto, necesitarás cambiar esa política o usar un repositorio personal.
9. En **Settings → Pages**, elige **Deploy from a branch → main → / (root) → Save**. Abre la URL `https://TU_USUARIO.github.io/abyss-wild-studio/` una vez publicado Pages.
10. Crea el token que utilizará **solo la página**: GitHub → **Settings de tu cuenta → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**. Repository access: **Only select repositories**, elige `abyss-wild-studio`. Repository permissions: **Actions → Read and write**; **Metadata → Read** viene automáticamente. Establece fecha corta de expiración. **No** pongas este token en Secrets ni en el código. No necesitas dar `Contents: write` al token del navegador; el `GITHUB_TOKEN` interno del workflow crea las Releases.
11. En la web de Pages, indica tu usuario y repo, introduce el fine-grained token y deja **Titanoboa** como tema. Pulsa **GENERAR SHORT**. Verás estado y enlace al workflow. Al finalizar, aparecerán enlaces separados para `video.mp4`, `guion.txt`, `fuentes.txt`, `creditos.txt`, `descripcion.txt` y `reporte.json`.
12. Descarga el MP4 en Android, revisa las afirmaciones y los créditos, y publícalo manualmente desde YouTube Studio o YouTube. En Chrome puedes pulsar **⋮ → Añadir a pantalla de inicio** para tener un acceso directo (requiere conexión; no es una aplicación offline).

## Opción de prueba sin usar Pages

GitHub → repositorio → **Actions → ABYSS WILD — Generador de Shorts → Run workflow → Tema: Titanoboa**. Si termina correctamente, visita **Releases** y descarga los archivos. Así puedes validar las API, el pipeline y las licencias antes de configurar el token del navegador.

## Costes, cuota y límites

- **Actions pública + runner estándar:** GitHub no factura minutos de ejecución; privada GitHub Free incluye 2.000 minutos mensuales. Se calcula en `reporte.json` una proyección de **6 × 30 × minutos por Short**; si supera 2.000 se registra una alerta. Límite orientativo para seis al día en privada: 11,1 minutos de Actions por video.
- **Gemini:** el programa usa un modelo Flash-Lite y pide 15 solicitudes/minuto como máximo, pero el límite diario RPM/TPM real de cada cuenta depende del panel Google AI Studio. El contador registra tokens informados por la API. Asume coste cero **solo si la clave sigue en el nivel gratuito**. El script no consulta la facturación de Google ni impide tarifas de una cuenta facturable.
- **Presupuesto:** `budget.py` lee el costo estimado de las Releases del mes y cancela antes de investigar si el máximo configurable quedaría superado. En repos privados reserva de forma conservadora 90 minutos por ejecución a la tarifa introducida. El costo de acciones públicas se estima en S/0. Este contador es orientativo y no sustituye los límites oficiales de gasto de cada proveedor. No contabiliza trabajos fallidos que no llegaron a crear Release ni otros repositorios.
- **Ritmo:** inicia con 2 o 3 videos diarios; con 6 diarios habrá mayor consumo de límites Gemini, CPU y red. Las ejecuciones se ponen en cola para que el contador de Releases no se solape.
- **Almacenamiento:** las Releases públicas pueden crecer con el tiempo. Borra manualmente Releases antiguas si ya descargaste sus videos, sabiendo que eso también borra el historial usado por el contador mensual.

## Comprobación

- [ ] La URL de Pages se abre en Android y conserva el usuario/repositorio.
- [ ] El token solo aparece en el navegador y tiene Actions read/write (sin permiso de escribir código).
- [ ] Actions permite ejecutar Titanoboa y las claves permanecen en Secrets.
- [ ] Los pasos Investigación, voz, imágenes, render, FFmpeg y validación terminan en verde.
- [ ] Existe una Release `short-ID` con cinco entregables y el reporte JSON.
- [ ] `video.mp4` abre en Android en 1080×1920 y dura de 30 a 45 segundos.
- [ ] La voz, los subtítulos y los cortes se corresponden; revisa cualquier imagen engañosa.
- [ ] `fuentes.txt` permite contrastar cada afirmación y `creditos.txt` identifica material de terceros.
- [ ] `descripcion.txt` contiene `#Shorts` y el aviso de voz e ilustraciones sintéticas.
- [ ] Nadie publicó el video en YouTube automáticamente.
- [ ] `reporte.json` indica duración, LUFS, tokens, render y alerta de cuota a seis diarios.

## Fallos más habituales

- **Error 401/403 al generar desde Pages:** verifica la caducidad del token y Actions read/write; no uses `GITHUB_TOKEN` del workflow en el navegador.
- **El workflow no aparece:** asegúrate de que `generate.yml` esté en la rama `main` bajo `.github/workflows/`.
- **Error 404 al descargar:** espera a que el workflow esté en estado `success`; verifica que exista la Release.
- **Gemini devuelve 429:** cuenta gratuita agotada temporalmente. Reintentos automáticos hasta cuatro intentos por solicitud. Espera que se restablezca el cupo.
- **No se consigue un guion verificable o medios correctos:** el proceso cancela o usa infografías, nunca reemplaza un animal prehistórico por otro sin etiquetar.
- **Voz Azure falla o faltan credenciales:** necesitas `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION` y un recurso Azure AI Speech con voz neural disponible. No se sustituye automáticamente por Piper, eSpeak ni voces inglesas. Consulta [README_VOZ.md](README_VOZ.md).
- **Instalación Node/Chromium tarda:** la caché npm/pip reduce nuevas instalaciones, pero el navegador Remotion y los codecs pueden necesitar descargas.

## Riesgos y supuestos expresos

1. Un usuario individual puede utilizar la licencia gratuita de Remotion, de acuerdo con los términos vigentes para esa categoría; si el proyecto pasa a ser operado por una organización no elegible, revisa la licencia.
2. La verificación con Gemini y las citas literales es una barrera de seguridad factual, **no** prueba matemática de cada afirmación ni revisión de expertos. Antes de publicar, verifica las fuentes.
3. El selector realiza **dos intentos por escena** para encontrar y validar recursos. Si fallan, transforma **esa escena visual** en infografía. Errores de FFmpeg/Remotion o desbordes ópticos finales detienen el workflow: no existe una reparación de frames de video ya renderizado sin re-renderizar la composición. La seguridad de subtítulos se basa en límites de texto y CSS, no OCR.
4. En Wikimedia, CC BY-SA puede imponer obligaciones de atribución y condiciones de compartir igual a material adaptado: conserva los créditos y revisa las obligaciones según el uso concreto. Pexels es gratis para uso permitido, no CC0.
5. Pexels se usa si se proporciona clave válida; contenido insuficiente se reemplaza por gráficos originales.
6. La versión requiere instalar paquetes y descargar Whisper `small` desde Internet; la voz nativa de Azure aún no se ha probado con tus claves. El flujo fallará expresamente si no se configura Azure Speech.

### Voces españolas nativas — configuración actual

Esta versión **requiere dos Secrets de Azure Speech**, además de la clave de Gemini: `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION`. Elige `es-PE-AlexNeural`, `es-PE-CamilaNeural`, `es-CO-GonzaloNeural`, `es-CO-SalomeNeural` o `es-MX-JorgeNeural` en `config.json`. El sistema valida el Locale devuelto por Azure. No existe fallback automático.

Lee [README_VOZ.md](README_VOZ.md) para habilitar el recurso Speech, ejecutar [el banco de voces](.github/workflows/voice_test.yml), editar `pronunciacion.json` (30 términos) y descargar el reporte Whisper. Sin credenciales Azure, la producción cancela la ejecución antes de sintetizar; los límites/cuotas y eventuales cargos dependen del recurso elegido.

### Recuperación de guiones sin perder verificación

En caso de que un borrador use pronombres o sinónimos (por ejemplo «la serpiente» tras mencionar «Titanoboa»), ya no se exige repetir palabras del tema en un porcentaje fijo de escenas. El gancho, título y cierre siguen protegiendo la identidad de temas de una sola palabra, y un auditor de Gemini comprueba por separado la pertinencia temática y el respaldo factual de cada frase.

Si el auditor rechaza una o varias escenas, **solo esas frases se reescriben** con los fragmentos de fuente disponibles; la nueva versión se vuelve a auditar. Hay un máximo de dos tandas de reparación por borrador y tres borradores por solicitud. Una reparación no verificada nunca se publica. Si no hay evidencia suficiente, la ejecución fallará deliberadamente para evitar un Short engañoso.

Las correcciones se prueban con `python -m unittest discover -s tests` desde GitHub Actions; estas pruebas no sustituyen ejecutar un video real con Gemini y revisar su resultado.
