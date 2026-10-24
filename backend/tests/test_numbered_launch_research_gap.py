"""Neutral launch discovery controls; no remote calls or historical answers."""
import unittest

import helpers
from app.core.pipeline import (
    _numbered_launch_research_query, _research_query_text, _research_scope_plan,
)
from app.services.source_queries import neutral_source_query


class NumberedLaunchResearchGapTests(unittest.TestCase):
    def test_disputed_calendar_never_replaces_the_numbered_mission_identity(self):
        for program, roman, number in (("Aurora", "IX", 9), ("Lunar Borealis", "IV", 4)):
            with self.subTest(program=program):
                first = f"A missão {program} {roman} foi lançada em 11 de maio de 2001."
                changed = first.replace("11 de maio de 2001", "19 de junho de 2002")
                query = _numbered_launch_research_query(first)
                self.assertEqual(query, _numbered_launch_research_query(changed))
                self.assertIn(f'"{program.lower()} {number}"', query)
                self.assertIn(f'"{program.lower()} {roman}"', query)
                self.assertEqual(query, _numbered_launch_research_query(first.replace(roman, str(number))))
                self.assertIn("mission", query)
                self.assertIn("launch", query)
                self.assertIn("lançamento", query)
                for date in ("2001", "2002", "maio", "junho"):
                    self.assertNotIn(date, query)
                self.assertEqual(first, f"A missão {program} {roman} foi lançada em 11 de maio de 2001.")

    def test_explicit_nondate_qualifiers_remain_in_discovery(self):
        claim = ("ESA’s uncrewed Aurora 9 mission successfully launched from Kennedy Space Center "
                 "at 1:47 a.m. EST on May 11, 2001.")
        query = _numbered_launch_research_query(claim)
        for qualifier in ('"aurora 9"', "esa", "uncrewed", "successfully", "kennedy space center", "01:47 EST"):
            self.assertIn(qualifier, query)
        self.assertNotIn("2001", query)
        self.assertNotEqual(query, _numbered_launch_research_query(claim.replace("Aurora 9", "Aurora 8")))
        self.assertNotEqual(query, _numbered_launch_research_query(claim.replace("ESA", "NASA")))

    def test_ambiguous_planned_qualified_and_recurring_vehicle_claims_keep_full_input_fallback(self):
        direct = "A missão Aurora IX foi lançada em 11 de maio de 2001."
        claims = (
            direct.replace("foi lançada", "será lançada"),
            direct.replace("foi lançada", "não foi lançada"),
            direct[:-1] + " com quatro astronautas.",
            direct + " A missão Borealis IV também foi lançada.",
            direct.replace("IX", "IIII"),
            "O foguete Saturn V lançou a espaçonave Aurora IX em 11 de maio de 2001.",
            "The Aurora 9 rocket launched on May 11, 2001.",
            "A pesquisadora Aurora publicou um estudo em 2001.",
        )
        for claim in claims:
            with self.subTest(claim=claim):
                self.assertIsNone(_numbered_launch_research_query(claim))
                operations, _ = _research_scope_plan(claim, [], [])
                self.assertEqual(len(operations), 1)
                self.assertEqual(operations[0]["query"], neutral_source_query(claim, preserve_period=True))
                self.assertEqual(operations[0]["scope_change_reason"], "original_neutral_editorial_gap")

    def test_failed_planner_gap_remains_one_bounded_operation_and_never_retries_same_query(self):
        claim = "A missão Aurora IX foi lançada em 11 de maio de 2001."
        operations, audit = _research_scope_plan(claim, [], [claim])
        self.assertEqual(len(operations), 1)
        item = operations[0]
        self.assertEqual(item["source_group"], "editorial")
        self.assertEqual(item["scope_change_reason"], "original_numbered_mission_editorial_gap")
        self.assertEqual(item["query_origin"], "deterministic_original_neutral")
        self.assertEqual(audit["deterministic_gap_query_count"], 1)
        self.assertLessEqual(len(_research_query_text(item["query"], "editorial")), 500)
        editorial = _research_query_text(item["query"], "editorial")
        second, audit = _research_scope_plan(claim, [], [claim, editorial])
        self.assertEqual(second[0]["source_group"], "any")
        self.assertEqual(second[0]["query"], item["query"])
        self.assertEqual(second[0]["scope_change_reason"], "duplicate_editorial_query_already_executed")
        third, audit = _research_scope_plan(claim, [], [claim, editorial, item["query"]])
        self.assertEqual(third, [])
        self.assertEqual(audit["deterministic_gap_query_count"], 0)

    def test_valid_model_editorial_queries_are_not_rewritten_or_given_extra_slots(self):
        claim = "A missão Aurora IX foi lançada em 11 de maio de 2001."
        explicit = {"query": "Aurora IX missão histórico lançamento original", "source_group": "editorial"}
        operations, audit = _research_scope_plan(claim, [explicit], [])
        self.assertEqual([(row["query"], row["source_group"]) for row in operations],
                         [(explicit["query"], explicit["source_group"])])
        self.assertEqual(audit["deterministic_gap_query_count"], 0)
        primary = {"query": "Aurora IX missão lançamento registro oficial", "source_group": "primary"}
        operations, _ = _research_scope_plan(claim, [primary], [])
        self.assertEqual(len(operations), 2)
        self.assertEqual(operations[0]["query"], primary["query"])
        self.assertEqual(operations[1]["query"], _numbered_launch_research_query(claim))

    def test_unknown_oversized_frames_are_not_partially_trimmed_into_search_aliases(self):
        name = " ".join(["A" + "b" * 35] * 4)
        owner = " ".join(["C" + "d" * 35] * 4)
        claim = f"The {name} IX mission of {owner} launched on May 11, 2001."
        self.assertIsNone(_numbered_launch_research_query(claim))
        for invalid in (None, {}, "", "Aurora IX launched."):
            with self.subTest(invalid=invalid):
                self.assertIsNone(_numbered_launch_research_query(invalid))


if __name__ == "__main__":
    unittest.main()
