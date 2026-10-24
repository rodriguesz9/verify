"""Bounded lexical bindings; synthetic controls, not a live accuracy score."""
import unittest

from app.services.classification_body_dates import classification_body_binding


class ClassificationBodyDatesTests(unittest.TestCase):
    claim = "Em 18 de abril de 2014, o Conselho Aurora caracterizou a FA-7 como uma pandemia."
    definition = (
        "The Aurora fever (FA-7) pandemic is a global outbreak of auroravirus – "
        "an infectious disease caused by Aurora virus (AV-2)."
    )
    bridge = (
        "Cases of novel auroravirus (nAv) were first detected in Vale Norte in February 2014, "
        "with the virus spreading rapidly to other countries across the world."
    )
    coordinated = (
        "This led Conselho Aurora to declare a Public Health Emergency of Regional Concern (PHERC) "
        "on 7 March 2014 and to characterize the outbreak as a pandemic on 18 April 2014."
    )

    def passage(self):
        return " ".join((self.definition, self.bridge, self.coordinated))

    def bind(self, claim=None, quote=None, context=None):
        quote = self.passage() if quote is None else quote
        return classification_body_binding(self.claim if claim is None else claim,
                                           quote, quote if context is None else context)

    def test_coordinated_dates_remain_bound_to_their_own_literal_classifications(self):
        quote = self.passage()
        context = "Documento público. " + quote + " Informações adicionais."
        proof = self.bind(context=context)
        self.assertIsNotNone(proof)
        self.assertEqual(proof["date"], "2014-04-18")
        self.assertEqual(proof["matched_clause"], 1)
        self.assertEqual([clause["date"] for clause in proof["clauses"]], ["2014-03-07", "2014-04-18"])
        self.assertEqual(proof["antecedent"], {"definition": self.definition, "bridge": self.bridge})
        self.assertEqual(proof["quote"], quote)
        self.assertEqual(proof["context"], context)
        self.assertEqual(proof["claim"], self.claim)
        self.assertIn("Public Health Emergency", proof["clauses"][0]["literal"])

    def test_unrelated_organization_identity_and_valid_dates_are_not_registered_answers(self):
        quote = self.passage().replace("Conselho Aurora", "Comissão Boreal").replace("FA-7", "CB-4")
        quote = quote.replace("18 April 2014", "29 February 2016").replace("7 March 2014", "8 June 2013")
        claim = self.claim.replace("Conselho Aurora", "Comissão Boreal").replace("FA-7", "CB-4")
        claim = claim.replace("18 de abril de 2014", "29 de fevereiro de 2016")
        proof = self.bind(claim, quote)
        self.assertEqual(proof["actor"], "comissão boreal")
        self.assertEqual(proof["date"], "2016-02-29")
        self.assertEqual(proof["clauses"][0]["date"], "2013-06-08")

    def test_explicit_named_subject_needs_no_anaphoric_inference(self):
        quote = (
            "Aurora Council declared a regional emergency on 4 January 2012 and "
            "characterized Aurora fever as a pandemic on 17 June 2012."
        )
        claim = "On 17 June 2012, Aurora Council classified Aurora fever as a pandemic."
        proof = self.bind(claim, quote)
        self.assertEqual(proof["date"], "2012-06-17")
        self.assertIsNone(proof["antecedent"])
        trailing = "Aurora Council characterized Aurora fever as a pandemic on June 17, 2012."
        self.assertIsNotNone(self.bind(trailing, quote))

    def test_direct_portuguese_clause_and_immediate_definition_are_supported(self):
        quote = (
            self.definition + " Isso levou Conselho Aurora a declarar uma emergência regional em 7 de março de 2014 "
            "e a caracterizar o surto como uma pandemia em 18 de abril de 2014."
        )
        self.assertIsNotNone(self.bind(quote=quote))

    def test_wrong_actor_subject_date_label_or_added_qualifier_abstains(self):
        for claim in (
            self.claim.replace("Conselho Aurora", "Conselho Boreal"),
            self.claim.replace("FA-7", "FA-8"),
            self.claim.replace("18 de abril", "7 de março"),
            self.claim.replace("pandemia", "epidemia"),
            self.claim.replace("pandemia.", "pandemia mundial."),
            self.claim.replace("FA-7", "grave FA-7"),
            self.claim.replace("caracterizou", "caracterizou oficialmente"),
            self.claim.replace("caracterizou", "não caracterizou"),
        ):
            with self.subTest(claim=claim):
                self.assertIsNone(self.bind(claim=claim))

    def test_first_date_cannot_be_borrowed_from_a_different_classification(self):
        swapped = self.coordinated.replace("7 March 2014", "18 April 2014").replace(
            "on 18 April 2014.", "on 7 March 2014.")
        self.assertIsNone(self.bind(quote=" ".join((self.definition, self.bridge, swapped))))
        loose = self.coordinated.replace("on 18 April 2014", "") + " 18 April 2014."
        self.assertIsNone(self.bind(quote=" ".join((self.definition, self.bridge, loose))))

    def test_invalid_other_date_and_duplicate_classifications_abstain(self):
        for replacement in (
            self.coordinated.replace("7 March 2014", "30 February 2014"),
            self.coordinated.replace("a Public Health Emergency of Regional Concern (PHERC)", "a pandemic"),
            self.coordinated.replace("a Public Health Emergency of Regional Concern (PHERC)", "a global pandemic"),
            self.coordinated[:-1] + " and to characterize the outbreak as a pandemic on 19 April 2014.",
            self.coordinated.replace("This led ", ""),
            self.coordinated.replace("to characterize", "characterized"),
        ):
            with self.subTest(replacement=replacement):
                self.assertIsNone(self.bind(quote=" ".join((self.definition, self.bridge, replacement))))

    def test_context_title_cannot_supply_missing_body_antecedent(self):
        self.assertIsNone(self.bind(quote=self.coordinated, context=self.passage()))
        self.assertIsNone(self.bind(quote=self.bridge + " " + self.coordinated, context=self.passage()))
        unrelated = self.passage().replace("Cases of novel auroravirus", "Cases of novel borealvirus")
        self.assertIsNone(self.bind(quote=unrelated))
        self.assertIsNone(self.bind(quote=self.passage().replace(self.bridge, "Outra observação.")))
        ambiguous = self.passage().replace("Aurora fever (FA-7)", "Aurora fever or Boreal fever (FA-7)")
        self.assertIsNone(self.bind(quote=ambiguous))

    def test_negation_fiction_uncertainty_and_quotation_preserve_abstention(self):
        for prefix in ("Relato fictício. ", "This event is hypothetical. ", "This was simulated. ",
                       "This is a false claim. ", "O órgão não fez essa caracterização. ",
                       "According to an alleged account. ", "There was no such classification. ",
                       "O órgão ficou sem qualquer classificação. "):
            with self.subTest(prefix=prefix):
                self.assertIsNone(self.bind(context=prefix + self.passage()))
        self.assertIsNone(self.bind(quote=self.passage().replace("to characterize", "not to characterize")))
        self.assertIsNone(self.bind(quote=self.passage().replace("This led", "This could lead")))

    def test_contract_does_not_accept_missing_oversize_or_nontext_inputs(self):
        for args in ((None, self.passage(), self.passage()), (self.claim, None, self.passage()),
                     (self.claim, self.passage(), ""), (self.claim, self.passage(), "x" * 3601)):
            with self.subTest(args_type=tuple(type(value) for value in args)):
                self.assertIsNone(classification_body_binding(*args))


if __name__ == "__main__":
    unittest.main()
