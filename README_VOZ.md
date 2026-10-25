# ABYSS WILD — voces españolas nativas y control de pronunciación

## Arquitectura

La voz de producción ya **no usa `edge-tts`, Piper ni eSpeak**. Usa el SDK oficial **Azure AI Speech** con una voz incluida en `config.json`. Por diseño, si Azure falla, el modelo no está disponible o su Locale no es español, **falla la ejecución**. No se produce una voz de emergencia.

Voces autorizadas y su Locale exigido:

| Identificador | Locale | Perfil |
|---|---|---|
| `es-PE-AlexNeural` | `es-PE` | Peruano masculino |
| `es-PE-CamilaNeural` | `es-PE` | Peruana femenina |
| `es-CO-GonzaloNeural` | `es-CO` | Colombiano masculino |
| `es-CO-SalomeNeural` | `es-CO` | Colombiana femenina |
| `es-MX-JorgeNeural` | `es-MX` | Mexicano masculino |

No se permiten identificadores Multilingual ni `en-*`. El script consulta la lista de voces del recurso y valida **el atributo Locale devuelto por Azure** antes de sintetizar.

## Configuración obligatoria en GitHub desde Android

1. Crea un **recurso Speech** de Azure, comprueba si tienes disponible el plan gratuito **F0** y revisa tus cuotas y condiciones. El servicio puede exigir una cuenta de Azure y datos de facturación según tu elegibilidad: **no es la API gratuita de Gemini**.
2. En el recurso Azure Speech, copia **Key 1** y **Region**. No compartas la clave ni la incluyas en `config.json`.
3. En `https://github.com/aldo200908-lgtm/abyss-wild-studio/settings/secrets/actions`, crea `AZURE_SPEECH_KEY` (el valor de Key 1) y `AZURE_SPEECH_REGION` (identificador como `eastus`, **solo si esa es la región real del recurso**).
4. Edita solo `config.json` para seleccionar una de las cinco voces. La opción predeterminada es `es-PE-AlexNeural`, con rate de -2 %.
5. Ejecuta `voice_test.yml` desde GitHub Actions. Descarga el artifact `banco_voces_espanolas`, extrae `banco_voces_espanolas.zip`, escucha los cinco MP3 numerados y lee el info.txt asociado a cada uno.
6. Cambia `voice` en `config.json` y ejecuta `generate.yml`. Mantén Gemini configurado como antes.

**No actives facturación de pago sin revisar sus condiciones.** Los caracteres de TTS de Azure tienen límites y, si se usa un recurso de pago, pueden generar cargos.

## Qué hace el sistema antes de publicar

* `spanish_voice_text.py`: extiende números, rangos y unidades, porcentajes, fechas y siglas conocidas; aplica la conjunción española `o/u`; elimina signos que podrían dificultar la voz; rechaza siglas desconocidas.
* `pronunciacion.json`: banco inicial editable con **30 entradas**, elegidas para paleontología, geología, Colombia y Perú. Cada entrada propone una forma de pronunciar. **Estas formas no están validadas por un hablante nativo**: hay que escucharlas; no son transcripciones IPA.
* `native_spanish_voice.py`: une frases de 8 a 18 palabras; sintetiza un WAV por frase con -4 % a 0 % de velocidad; inserta pausas pseudoaleatorias de 0,2 a 0,5 segundos; combina WAV y convierte a MP3 con FFmpeg.
* `faster-whisper` modelo `small` con idioma `es` y CPU `int8`: transcribe el MP3, lo compara con el texto normalizado mediante distancia de edición por palabras y **falla por debajo de 92 %**. Almacena palabras sospechosas en `dist/pronunciacion_reporte.txt`, también disponible en un artifact de GitHub incluso si la transcripción falla.
* `pipeline.py`: incorpora medidas de LUFS, pico interpolado a cuatro veces la frecuencia (`true_peak_dbtp_4x`), número y duración de pausas, y fracción de energía vocal por encima de 4 kHz. Exige como máximo -1,5 dBTP aproximados al archivo final. Publica `audio_calidad.json` y un campo de calidad en `reporte.json`.

**Precisión:** Whisper puede equivocar nombres científicos aunque la voz sea buena; las diferencias son *sospechas* y deben revisarse por oído. Las marcas de subtítulos son aproximadas por escena. El pico true peak medido por interpolación 4x es una estimación, no un medidor ITU-R BS.1770 certificado.

## Banco de voces: descarga

Accede a [voice_test.yml](https://github.com/aldo200908-lgtm/abyss-wild-studio/actions/workflows/voice_test.yml), pulsa **Run workflow**, escucha después el ZIP del artifact `banco_voces_espanolas`. Los archivos internos son `01_es-PE-AlexNeural.mp3`, `01_es-PE-AlexNeural_info.txt`, ..., `05_es-MX-JorgeNeural.mp3` y su info correspondiente. Si marcas **incluir_piper**, se añade una muestra opcional CPU **solamente para comparar**, nunca para sustituir una voz Azure ausente.

## Caso de prueba: Titanoboa

Frase de test: «La Titanoboa cerrejonensis vivió hace millones de años. Medía entre 12-14 m y pesaba 1.135 kg. Sus fósiles se hallaron en Cerrejón, Colombia».

Las cifras son una **demostración lingüística** del normalizador, no datos aprobados para el documental. El script `tests/test_voice_titanoboa.py` verifica expresiones, locale, duración de frases y correcciones, sin enviar solicitudes de pago. Antes de publicar un Short con datos numéricos, el guion todavía debe aprobar su investigación y validación factual.

## Archivos del cambio

`config.json`, `pronunciacion.json`, `spanish_voice_text.py`, `native_spanish_voice.py`, `voice_bank.py`, `pipeline.py`, `requirements.txt`, `.github/workflows/generate.yml`, `.github/workflows/voice_test.yml`, `README_VOZ.md`, pruebas en `tests/`. El código anterior `offline_voice.py` existe únicamente para la muestra opcional Piper y pruebas de compatibilidad: **no es importado por la ruta de producción**.

## Limitaciones

No se ha ejecutado una síntesis Azure autenticada desde esta conversación: faltan los Secrets reales del usuario. Las pruebas de unidad pueden aprobar sin demostrar que la nueva voz suene bien; la aprobación final exige generar el ZIP, escuchar las voces y verificar el nuevo MP4 y su informe ASR.
