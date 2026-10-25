# ABYSS WILD — Motor Edutainment v2 (Ubuntu / GitHub Actions)

Arquitectura modular sin interfaz gráfica: **Python + FFmpeg (zoompan, loudnorm,
silenceremove, sidechaincompress) + Remotion/React + Azure Speech + Whisper**.

## Estructura

| Archivo | Función |
| --- | --- |
| `pipeline.py` | Orquesta guion validado, medios, alineación, audio, render, QA |
| `viral_visuals.py` | Verifica imágenes, recorta a 9:16, FFmpeg zoompan, planos de 3–4 s y 3 PNG transparentes de mascota |
| `render/src/index.jsx` | Únicamente B-roll, subtítulos de una palabra al centro, gancho rojo y superposición de mascota |
| `native_spanish_voice.py` | Voz Jorge, recorte conservador de silencios de inicio/fin y ASR Whisper con word timestamps |
| `word_alignment.py` | Concilia marcas ASR con cada palabra real del guion (incluye cantidades escritas en cifras) |
| `audio_design.py` | Música original de misterio y SFX puntuales en 3 s y algunos cambios de escena |
| `smoke_render.py` | Prueba de render completo sin Secret ni conexiones de medios |
| `.github/workflows/generate.yml` | Ejecución de producción mediante botón Run workflow |
| `.github/workflows/tests.yml` | Pruebas Python + JS + visual/FFmpeg + render headless real |

## Ejecución en Ubuntu 24.04

Necesita Python 3.11, Node 22, FFmpeg con libx264, Git, conexión de red y
credenciales válidas para servicios externos. Todo el render funciona sin X11
y sin ventanas de escritorio.

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
python3 -m pip install -r requirements.txt
cd render && npm install --no-audit --no-fund && cd ..
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test render/tests/motion.test.mjs
python3 smoke_render.py
cd render && npm run render
```

El smoke test genera `work/silent.mp4` (video de prueba **sin voz**), que debe
mantener 1080×1920. Para producir Shorts reales se ejecuta
`generate.yml` y se selecciona el tema en **Run workflow**.

## Cinco modificaciones implementadas

1. **Sin UI:** no hay títulos, etiquetas, gráficas ornamentales, barras de
   progreso ni párrafos estáticos. La transición de 3 segundos es momentánea.
2. **B-roll obligatorio:** cada beat de 3 a 4 segundos tiene una imagen o video
   aprobado, normalizado a 1080×1920. Las fotografías reciben FFmpeg
   `zoompan` (zoom in/out o paneo). Se detectan imágenes uniformes y frames
   vacíos en muestras de inicio, mitad y final. Si no hay imagen pertinente
   y con licencia aceptable, **el pipeline se detiene**: no inventa fondos.
3. **Subtítulos:** una palabra por vez, centrada en píxel (540,960), Anton en
   mayúsculas, borde negro grueso y sombra. Las palabras clave del gancho
   tienen rojo y resplandor. Whisper proporciona tiempos por palabra; cuando
   Whisper no reconoce una palabra, se usa el estimado de su grupo TTS
   (no se hace pasar por alineación fonética exacta).
4. **Audio:** Azure Speech conserva la velocidad natural seleccionada.
   FFmpeg elimina silencio al inicio/final de cada fragmento sin cortar pausas
   internas. No hay silencios **añadidos** entre fragmentos. BGM sintética
   original se nivela a 20 LUFS menos que la voz y se hace ducking; efecto
   grave al segundo 3 y ambiente en algunos cortes. La exportación comprueba
   LUFS y true peak AAC, con hasta 4 nuevos intentos desde los originales.
5. **Mascota:** tres PNG RGBA originales generados por `make_mascots`:
   sorprendido, pensando, feliz; aparecerá deslizándose desde el borde inferior
   en 0–3 segundos y en otros dos momentos durante ~4 s.

## Seguridad editorial y de derechos

- Solo se aceptan candidatos de Wikimedia con metadatos de licencia válidos y
  clips gratuitos de Pexels que pasen la auditoría de pertinencia visual.
- No se reutiliza un animal o fósil no relacionado para representar otro.
- Se dejan las atribuciones en `creditos.txt` y `descripcion.txt`.
- No se publica contenido que falle las validaciones de audio, escena, medios,
  transcripción, o resolución.
- Los PNG de mascota son originales y están generados localmente; puedes
  reemplazarlos más adelante por diseños de tu marca conservando sus nombres.

## Comprobación antes de publicar

1. GitHub Actions — **ABYSS WILD - Pruebas de codigo** debe aparecer verde,
   incluida la prueba `HEADLESS_BROLL_RENDER_OK`.
2. Ejecuta **ABYSS WILD — Generador de Shorts** con un tema nuevo.
3. Revisa `video.mp4`, `pronunciacion_reporte.txt`,
   `audio_calidad.json`, `guion.txt`, `fuentes.txt` y `creditos.txt` en
   la Release. El QA automático nunca sustituye la revisión de imágenes,
   derechos, voz y montaje antes de publicar.

**Nota:** La duración completa del pipeline de producción depende de la
disponibilidad de imágenes/medios con licencia, las API externas y el runner.
Un resultado verde en CI verifica código y render de prueba, no garantiza que
un tema concreto tenga suficientes recursos B-roll disponibles.
