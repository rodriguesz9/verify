"""Offline query/segmentation controls, not factual accuracy benchmarks."""
from datetime import datetime, timezone
import json
import unittest

from app.services.claim_policy import input_claims, text_report
from app.services.factual_queries import build_fact_check_queries


class LiteralSentenceTests(unittest.TestCase):
    def test_titles_remain_attached_to_the_name(self):
        for title in ("Dr.", "Dra.", "Sr.", "Sra.", "Prof.", "Profa.", "DR."):
            text = f"O {title} Silva anunciou a medida. Outra afirmação."
            with self.subTest(title=title):
                self.assertEqual(input_claims(text), [f"O {title} Silva anunciou a medida.", "Outra afirmação."])

    def test_abbreviation_with_line_wrap_preserves_literal_whitespace(self):
        self.assertEqual(input_claims("A Dra.\nSilva anunciou a medida.\nOutra afirmação."),
                         ["A Dra.\nSilva anunciou a medida.", "Outra afirmação."])

    def test_internal_number_date_and_unicode_punctuation_are_preserved(self):
        claim = "A Dra. Ávila não recebeu R$ 1.500,00 em 08.09.2022 nem 10,5% em 14/10/2026."
        self.assertEqual(input_claims(claim + " Próxima afirmação."), [claim, "Próxima afirmação."])
        self.assertEqual(input_claims("Valor 1.000,00. Data 2026-10-10. Razão 1.5."),
                         ["Valor 1.000,00.", "Data 2026-10-10.", "Razão 1.5."])

    def test_title_fix_does_not_weaken_exact_evidence_or_negation(self):
        claim = "A Dra. Ávila recebeu R$ 1.500,00 em 08.09.2022."
        reviews = [{"claim_text": claim, "rating": "Verdadeiro", "url": f"https://{domain}/synthetic",
                    "review_date": "2026-09-01T00:00:00Z", "retrieval_provider": "google_fact_check"}
                   for domain in ("aosfatos.org", "boatos.org")]
        now = datetime(2026, 10, 10, tzinfo=timezone.utc)
        self.assertEqual(text_report(claim, reviews, now=now)["veracity_status"], "supported")
        for changed in (claim.replace("recebeu", "não recebeu"), claim.replace("1.500,00", "150,00"),
                        claim.replace("08.09.2022", "09.09.2022"), claim + " Hoje."):
            with self.subTest(changed=changed):
                self.assertEqual(text_report(changed, reviews, now=now)["veracity_status"], "unverified")


class FactualQueryPlanTests(unittest.TestCase):
    def test_extracted_fifth_sentence_is_not_crowded_out_by_headings(self):
        fact = "O município de Exemplo inaugurou a ponte em 2024."
        text = "Título do artigo\nPor Autor\nPublicado em 2026\nCompartilhe este texto\n" + fact
        queries, audit = build_fact_check_queries(text, [fact])
        self.assertEqual(queries[0], fact)
        self.assertIn(text, queries)
        self.assertEqual(len(queries), 5)
        self.assertEqual(audit["omitted_count"], 1)
        self.assertEqual(audit["literal_segments_not_queried_separately"], 1)
        self.assertTrue(audit["whole_text_queried"])
        self.assertEqual(audit["query_methods"][0], "extracted_literal_sentence")

    def test_complete_input_reserved_when_extractions_fill_the_budget(self):
        claims = [f"A cidade {number} abriu uma ponte." for number in range(5)]
        text = " ".join(claims)
        queries, audit = build_fact_check_queries(text, claims)
        self.assertEqual(queries, [*claims[:4], text])
        self.assertEqual(audit["selected_count"], 5)
        self.assertEqual(audit["literal_segments_not_queried_separately"], 1)

    def test_queries_are_deduplicated_without_rewriting_input(self):
        text = "  A Ávila recebeu R$ 1.500,00 em 14/10/2026.  "
        queries, audit = build_fact_check_queries(text, [text.strip(), text.strip()])
        self.assertEqual(queries, [text.strip()])
        self.assertEqual(audit["selected_count"], 1)
        self.assertEqual(audit["omitted_count"], 0)
        self.assertTrue(audit["whole_text_queried"])

    def test_partial_hint_retains_negation_date_value_and_relative_context(self):
        text = "Não é verdade que a Dra. Ávila recebeu R$ 1.500,00 em 14/10/2026 hoje. Outra afirmação."
        queries, audit = build_fact_check_queries(text, ["a Dra. Ávila recebeu R$ 1.500,00"])
        self.assertEqual(queries[0], input_claims(text)[0])
        self.assertIn("Não é verdade", queries[0])
        self.assertIn("14/10/2026 hoje", queries[0])
        self.assertEqual(audit["extracted_valid_count"], 1)

    def test_nonliteral_or_cross_sentence_extractions_are_rejected(self):
        text = "A avó recebeu R$ 10. Ela não recebeu R$ 20."
        queries, audit = build_fact_check_queries(text, ["A avo recebeu R$ 10", "Ela recebeu R$ 20", None,
                                                         "", "10. Ela não", "A avó recebeu R$ 10"])
        self.assertNotIn("Ela recebeu R$ 20", queries)
        self.assertEqual(audit["extracted_valid_count"], 1)
        self.assertEqual(audit["extracted_rejected_count"], 5)
        self.assertTrue(all(query in text for query in queries))

    def test_repeated_partial_hint_keeps_both_literal_contexts(self):
        text = "A cidade abriu a ponte. Não é verdade que a cidade abriu a ponte."
        queries, _ = build_fact_check_queries(text, ["cidade abriu a ponte"])
        self.assertIn("A cidade abriu a ponte.", queries)
        self.assertIn("Não é verdade que a cidade abriu a ponte.", queries)

    def test_oversize_input_is_omitted_and_never_silently_cut(self):
        long_sentence = "A cidade " + "Á" * 5000 + " não recebeu R$ 1.500,00 hoje."
        fact = "A Dra. Ávila não recebeu R$ 20 em 14/10/2026."
        text = long_sentence + "\n" + fact
        queries, audit = build_fact_check_queries(text, [long_sentence, fact])
        self.assertEqual(queries, [fact])
        self.assertEqual(audit["oversize_candidate_count"], 2)
        self.assertFalse(audit["whole_text_queried"])
        self.assertFalse(audit["truncated"])

    def test_one_slot_prioritizes_literal_extraction_and_audit_contains_no_text(self):
        fact = "A Dra. Ávila não recebeu R$ 20 em 14/10/2026."
        queries, audit = build_fact_check_queries("Cabeçalho\n" + fact, [fact], limit=1)
        self.assertEqual(queries, [fact])
        self.assertFalse(audit["whole_text_queried"])
        serialized = json.dumps(audit)
        self.assertNotIn("Ávila", serialized)
        self.assertNotIn("Cabeçalho", serialized)
        self.assertEqual(len(audit["query_methods"]), len(queries))

    def test_empty_input_and_invalid_limit(self):
        queries, audit = build_fact_check_queries(" \n ", [])
        self.assertEqual(queries, [])
        self.assertEqual(audit["candidate_count"], 0)
        for limit in (0, -1, True, "5"):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                build_fact_check_queries("Uma afirmação.", [], limit=limit)


if __name__ == "__main__":
    unittest.main()
