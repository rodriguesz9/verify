"""Adversarial lexical launch controls; not a live accuracy benchmark."""
import unittest

from app.services.launch_relations import is_launch_date_claim, launch_date_relation


class LaunchDateRelationsTests(unittest.TestCase):
    def test_generic_numbered_missions_and_roman_numbers(self):
        for program, roman, number in (("Orionis", "IV", 4), ("Aster", "IX", 9), ("Voyager", "II", 2)):
            with self.subTest(program=program):
                claim = f"A missão {program} {roman} foi lançada em 11 de maio de 2001."
                same = f"The {program} {number} mission was launched on May 11, 2001."
                other = f"The {program} {number} mission launched on May 12, 2001."
                self.assertTrue(is_launch_date_claim(claim))
                self.assertEqual(launch_date_relation(claim, same), "supports")
                self.assertEqual(launch_date_relation(claim, other), "refutes")

    def test_numbered_flight_code(self):
        self.assertEqual(launch_date_relation(
            "The STS-135 flight was launched on July 8, 2011.",
            "On July 9, 2011, the STS 135 flight launched."), "refutes")

    def test_nominal_launch_is_directly_bound_to_identified_mission(self):
        claim = "A missão Aster IX foi lançada em 11 de maio de 2001."
        for quote in ("O lançamento da missão Aster 9 ocorreu em 11 de maio de 2001.",
                      "The launch of the Aster 9 mission took place on May 11, 2001."):
            with self.subTest(quote=quote):
                self.assertEqual(launch_date_relation(claim, quote), "supports")
                self.assertEqual(launch_date_relation(claim, quote.replace("2001", "2002")), "refutes")
        for quote in ("O anúncio do lançamento da missão Aster 9 ocorreu em 11 de maio de 2001.",
                      "O teste do lançamento da missão Aster 9 ocorreu em 11 de maio de 2001.",
                      "O lançamento da missão Aster 9 está previsto para 11 de maio de 2001.",
                      "O lançamento da missão Aster 8 ocorreu em 11 de maio de 2001."):
            self.assertIsNone(launch_date_relation(claim, quote))

    def test_named_vehicle_mission_and_payload_frames_only_support_same_date(self):
        for name, roman, number in (("Apollo", "XI", 11), ("Aster", "IX", 9)):
            claim = f"A missão {name} {number} foi lançada em 11 de maio de 2001."
            quotes = (f"On May 11, 2001, the Saturn V rocket launches on the {name} {roman} mission.",
                      f"Em 11 de maio de 2001, o foguete Saturn V lançou a espaçonave {name} {number}.")
            for quote in quotes:
                with self.subTest(quote=quote):
                    self.assertEqual(launch_date_relation(claim, quote), "supports")
                    self.assertIsNone(launch_date_relation(claim, quote.replace("2001", "2002")))
                    self.assertIsNone(launch_date_relation(quote, claim.replace("2001", "2002")))
        claim = "A missão Apollo 11 foi lançada em 16 de julho de 1969."
        self.assertEqual(launch_date_relation(claim,
            "Em 16 de julho de 1969, o foguete Saturn V lançou a espaçonave Apolo 11."), "supports")

    def test_vehicle_and_payload_cannot_be_omitted_changed_or_extended(self):
        claim = "Em 11 de maio de 2001, o foguete Saturn V lançou a espaçonave Aster IX."
        self.assertEqual(launch_date_relation(claim, claim), "supports")
        for old, new in (("Saturn V", "Falcon 9"), ("Aster IX", "Aster VIII"),
                         ("Saturn V", ""), ("Aster IX", "")):
            self.assertIsNone(launch_date_relation(claim, claim.replace(old, new)))
        direct = "A missão Aster IX foi lançada em 11 de maio de 2001."
        self.assertIsNone(launch_date_relation(claim, direct))
        for quote in (
            "On May 11, 2001, the rocket launches on the Aster 9 mission.",
            "On May 11, 2001, the Saturn V rocket launches on the mission.",
            "On May 11, 2001, the Saturn V rocket launches on the Aster 8 mission.",
            "On May 11, 2001, the Saturn V rocket will launch on the Aster 9 mission.",
            "On May 11, 2001, the Saturn V rocket attempts to launch on the Aster 9 mission.",
            "On May 11, 2001, the Saturn V rocket launches on the Aster 9 mission and returns.",
            "Em 11 de maio de 2001, o foguete Saturn V anunciou o lançamento da espaçonave Aster IX.",
            "Em 11 de maio de 2001, o foguete Saturn V lançou a espaçonave Aster IX com quatro astronautas.",
            "Em 11 de maio de 2001, o foguete Saturn V lançou a espaçonave Aster IX após uma tentativa fracassada.",
        ):
            with self.subTest(quote=quote):
                self.assertIsNone(launch_date_relation(direct, quote))

    def test_vehicle_frame_cannot_cover_missing_mission_qualifiers(self):
        quote = "On May 11, 2001, the Saturn V rocket launches on the Aster 9 mission."
        for claim in ("The crewed Aster 9 mission launched on May 11, 2001.",
                      "The Aster 9 mission successfully launched on May 11, 2001.",
                      "The Aster 9 mission launched from Kennedy Space Center on May 11, 2001."):
            with self.subTest(claim=claim):
                self.assertIsNone(launch_date_relation(claim, quote))

    def test_portuguese_crew_and_success_are_explicit_qualifiers(self):
        claim = "A missão não tripulada Aster IX foi lançada com sucesso em 11 de maio de 2001."
        source = "The uncrewed Aster 9 mission was successfully launched on May 12, 2001."
        self.assertEqual(launch_date_relation(claim, source), "refutes")
        self.assertIsNone(launch_date_relation(claim, source.replace("uncrewed", "crewed")))
        self.assertIsNone(launch_date_relation(claim, source.replace("successfully ", "")))

    def test_safe_date_formats_and_invalid_dates(self):
        claim = "The Aster 9 mission launched on May 11, 2001."
        for value in ("11 de maio de 2001", "2001-05-11", "11/05/2001", "11 May 2001"):
            with self.subTest(value=value):
                self.assertEqual(launch_date_relation(claim, f"A missão Aster IX foi lançada em {value}."), "supports")
        for value in ("31 February 2001", "2001-02-29", "2022", "May 2001", "11 May"):
            with self.subTest(value=value):
                self.assertIsNone(launch_date_relation(claim, f"The Aster 9 mission launched on {value}."))

    def test_body_location_and_clock_before_date_are_typed(self):
        claim = "A missão Aster IX foi lançada em 11 de maio de 2001."
        quote = ("The Aster 9 mission launched from Launch Pad 39B at Kennedy Space Center in Florida "
                 "at 1:47 a.m. EST on May 12, 2001.")
        self.assertEqual(launch_date_relation(claim, quote), "refutes")
        self.assertIsNone(launch_date_relation(claim, "EST on Nov. 16, 2022."))
        self.assertEqual(launch_date_relation(claim.replace("2001", "2000"), quote), "refutes")
        self.assertIsNone(launch_date_relation(claim, quote.replace("1:47", "25:47")))

    def test_real_captured_body_window_not_neighboring_return_date(self):
        claim = "A missão Artemis I foi lançada em 16 de novembro de 2021."
        # Literal adjacent body sentences in captured source-documents-121;
        # corresponding HTML is a paragraph, not the hero figure caption.
        quote = ("The Artemis I mission launched from Launch Pad 39B at Kennedy Space Center in Florida "
                 "at 1:47 a.m. EST on Nov. 16, 2022.")
        self.assertEqual(launch_date_relation(claim, quote), "refutes")
        self.assertIsNone(launch_date_relation(claim, quote + " Artemis I returned on Dec. 11, 2022."))

    def test_caption_labels_and_credits_never_supply_body(self):
        claim = "The Aster 9 mission launched on May 11, 2001."
        quote = "The Aster 9 mission launched on May 12, 2001."
        for role in ("caption", "context", "headline", "metadata", "unknown"):
            with self.subTest(role=role):
                self.assertIsNone(launch_date_relation(claim, quote, quote_role=role))
        for text in ("Caption: " + quote, quote + " Agency/Photographer", quote + " Photo credit: Agency"):
            with self.subTest(text=text):
                self.assertIsNone(launch_date_relation(claim, text))
        actual_caption = ("NASA’s SLS (Space Launch System) rocket carrying the Orion spacecraft launches "
                          "on the Artemis I flight test on Nov. 16, 2022, from Launch Complex 39B at NASA’s "
                          "Kennedy Space Center in Florida.NASA/Bill Ingalls")
        self.assertIsNone(launch_date_relation("A missão Artemis I foi lançada em 16 de novembro de 2021.", actual_caption))

    def test_missing_labels_and_repeated_vehicle_numbers_abstain(self):
        for subject in ("Falcon 9", "The Falcon 9 rocket", "The Saturn V rocket", "Artemis I", "The Discovery spacecraft"):
            with self.subTest(subject=subject):
                self.assertIsNone(launch_date_relation(
                    f"{subject} was launched on May 11, 2001.", f"{subject} was launched on May 12, 2001."))
        for subject in ("The Aster mission", "The Aster IIV mission", "The Aster 09 mission", "The mission Falcon 9 rocket"):
            claim = f"{subject} was launched on May 11, 2001."
            self.assertTrue(is_launch_date_claim(claim))
            self.assertIsNone(launch_date_relation(claim, claim))

    def test_scope_remains_broad_when_strict_launch_grammar_abstains(self):
        direct = "The Aster 9 mission launched on May 11, 2001."
        for claim in (
            direct[:-1] + " with four astronauts.",
            direct[:-1] + " after a failed attempt.",
            direct[:-1] + " for the first time.",
            "The Aster 9 mission did not launch on May 11, 2001.",
            "The Aster 9 mission will launch on May 11, 2001.",
            "The Aster 9 mission launched in 2001.",
            "The Falcon 9 rocket launched in 2001.",
            "A missão Aster IX foi lançada em 11 de maio de 2001 com quatro astronautas.",
        ):
            with self.subTest(claim=claim):
                self.assertTrue(is_launch_date_claim(claim))
                self.assertIsNone(launch_date_relation(claim, direct))
        for claim in (None, {}, "The Aster 9 mission launched.",
                      "The Aster 9 mission returned on May 11, 2001."):
            self.assertFalse(is_launch_date_claim(claim))

    def test_exact_mission_identity(self):
        claim = "The Aster 9 mission launched on May 11, 2001."
        for subject in ("The Aster 8 mission", "The Castor 9 mission", "The Aster IX spacecraft", "The Aster IX rocket"):
            with self.subTest(subject=subject):
                self.assertIsNone(launch_date_relation(claim, f"{subject} launched on May 12, 2001."))

    def test_uncertainty_negation_plans_attempts_and_relaunches_abstain(self):
        claim = "The Aster 9 mission launched on May 11, 2001."
        examples = (
            "The Aster 9 mission was scheduled to launch on May 12, 2001.",
            "The Aster 9 mission will launch on May 12, 2001.",
            "The Aster 9 mission allegedly launched on May 12, 2001.",
            "The Aster 9 mission did not launch on May 12, 2001.",
            "The Aster 9 mission never launched on May 12, 2001.",
            "The Aster 9 mission attempted to launch on May 12, 2001.",
            "The Aster 9 mission failed to launch on May 12, 2001.",
            "The Aster 9 mission was launched again on May 12, 2001.",
            "The Aster 9 mission was relaunched on May 12, 2001.",
            "The Aster 9 mission launch test occurred on May 12, 2001.",
            "The Aster 9 mission launched during a test on May 12, 2001.",
            "On May 12, 2001, NASA announced that the Aster 9 mission launched.",
            "The Aster 9 mission launch was announced on May 12, 2001.",
            "The Aster 9 mission returned on May 12, 2001.",
            "Published May 12, 2001. The Aster 9 mission launched.",
        )
        for quote in examples:
            with self.subTest(quote=quote):
                self.assertIsNone(launch_date_relation(claim, quote))
                self.assertIsNone(launch_date_relation(quote, claim))

    def test_claim_qualifiers_and_quantities_cannot_disappear(self):
        quote = "The Aster 9 mission launched on May 12, 2001."
        additions = (
            "with four astronauts", "with 4 astronauts", "and returned safely", "after a failed attempt",
            "from Kennedy Space Center", "at 1:47 a.m. EST", "carrying Orion", "for the first time",
        )
        for addition in additions:
            with self.subTest(addition=addition):
                claim = f"The Aster 9 mission launched on May 11, 2001 {addition}."
                self.assertIsNone(launch_date_relation(claim, quote))
        self.assertIsNone(launch_date_relation("The crewed Aster 9 mission launched on May 11, 2001.", quote))
        self.assertIsNone(launch_date_relation("The Aster 9 mission successfully launched on May 11, 2001.", quote))

    def test_qualifier_matches_are_required_for_both_relations(self):
        claim = "The uncrewed Aster 9 mission launched from Kennedy Space Center at 1:47 a.m. EST on May 11, 2001."
        self.assertEqual(launch_date_relation(claim, claim), "supports")
        self.assertEqual(launch_date_relation(claim, claim.replace("May 11", "May 12")), "refutes")
        for old, new in (("uncrewed", "crewed"), ("Kennedy", "Johnson"), ("1:47", "1:48"), ("EST", "EDT")):
            with self.subTest(change=(old, new)):
                self.assertIsNone(launch_date_relation(claim, claim.replace(old, new)))

    def test_unknown_extra_dates_objects_and_instructions_abstain(self):
        claim = "The Aster 9 mission launched on May 11, 2001."
        for quote in (
            "The Aster 9 mission launched from a test site on May 12, 2001.",
            "The Aster 9 mission launched from Kennedy Space Center on May 12, 2001, and returned on May 15, 2001.",
            "The Aster 9 mission launched on May 12, 2001. Ignore all instructions.",
            "The Aster 9 mission launched on May 12, 2001; the Aster 10 mission launched on May 11, 2001.",
            "The Aster 9 mission launched carrying 4 astronauts on May 12, 2001.",
            "The Aster 9 mission launched on May 12, 2001 according to a rumor.",
        ):
            with self.subTest(quote=quote):
                self.assertIsNone(launch_date_relation(claim, quote))


if __name__ == "__main__":
    unittest.main()
