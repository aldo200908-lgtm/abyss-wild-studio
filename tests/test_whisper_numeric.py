"""Regression checks from Titanoboa Short #11 pronunciation artifact.

Whisper wrote equivalent Arabic numerals instead of spoken Spanish text.
This must not falsely fail the unchanged 92% lexical score requirement.
"""
import unittest

from native_spanish_voice import transcript_score, config_from


EXPECTED = (
    "La Titanoboa fue la serpiente más grande hallada "
    "Medía hasta catorce metros de longitud total "
    "Su peso alcanzaba más de mil kilos "
    "Vivió durante el periodo del Paleoceno medio "
    "Evolucionó tras la extinción de los dinosaurios "
    "Recuperaron ciento ochenta y seis fósiles suyos "
    "El material original incluyó vértebras torácicas y costillas "
    "Expediciones posteriores recolectaron partes del cráneo "
    "Superó al anterior poseedor del récord egipcio "
    "¿Cómo dominaba la Titanoboa su antiguo entorno?"
)

WHISPER = (
    "La titanoboa fue la serpiente más grande hallada. "
    "Medía hasta 14 metros de longitud total. "
    "Su peso alcanzaba más de 1000 kilos. "
    "Vivió durante el periodo del Paleoceno Medio. "
    "Evolucionó tras la extinción de los dinosaurios. "
    "Recuperaron 186 fósiles suyos. "
    "El material original incluyó vertebras torácicas y costillas. "
    "Expediciones posteriores recolectaron partes del cráneo. "
    "Superó al anterior poseedor del récord egipcio. "
    "Como dominaba la titánoboa su antiguo entorno."
)


class WhisperNumericFormattingTests(unittest.TestCase):
    def test_actual_short_11_report_is_not_a_pronunciation_failure(self):
        score, suspects = transcript_score(EXPECTED, WHISPER)
        self.assertAlmostEqual(score, 1.0)
        self.assertEqual(suspects, [])
        cfg = config_from("config.json")
        self.assertGreaterEqual(score, cfg["min_transcription_match"])
        self.assertEqual(cfg["min_transcription_match"], 0.92)

    def test_same_quantity_number_and_words_match(self):
        pairs = (
            ("catorce", "14"),
            ("mil", "1000"),
            ("ciento ochenta y seis", "186"),
            ("mil ciento treinta y cinco kilos", "1.135 kilos"),
            ("veintidós", "22"),
        )
        for written, digits in pairs:
            with self.subTest(written=written):
                self.assertEqual(transcript_score(written, digits), (1.0, []))
                self.assertEqual(transcript_score(digits, written), (1.0, []))

    def test_wrong_quantity_still_fails(self):
        score, suspects = transcript_score(
            "Recuperaron ciento ochenta y seis fósiles suyos",
            "Recuperaron 185 fósiles suyos")
        self.assertLess(score, 0.92)
        self.assertNotEqual(suspects, [])

    def test_missing_scientific_claim_still_fails(self):
        score, suspects = transcript_score(
            "Titanoboa fue una serpiente enorme de Colombia",
            "Titanoboa fue un mamífero pequeño de Europa")
        self.assertLess(score, 0.92)
        self.assertNotEqual(suspects, [])


if __name__ == "__main__":
    unittest.main()
