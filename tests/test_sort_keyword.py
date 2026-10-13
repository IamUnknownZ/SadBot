import unittest
from pathlib import Path

from services.answering import answer
from services.ingest import load_dataset
from services.retrieval import plan_query


ROOT = Path(__file__).resolve().parents[1]


class SortKeywordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(ROOT)

    def test_bare_sort_spellings_resolve_to_the_source_definition(self):
        expected_passages = [
            "sort a sequence of numbers into nondecreasing",
            "Input: A sequence of n numbers",
            "given the input sequence",
        ]
        for query in ("sort", "SORT", "ซอส", "S-O-R-T", "sort คืออะไร"):
            with self.subTest(query=query):
                plan = plan_query(query)
                self.assertEqual(plan["topics"], ["principles"])
                result = answer(query, self.data, ROOT,
                                select_generate=lambda _: self.fail("A bare sort term should use its direct source route"))
                self.assertEqual(result["status"], "answered")
                self.assertEqual([row["page"] for row in result["evidence"]], [5, 5, 5])
                for phrase, row in zip(expected_passages, result["evidence"]):
                    self.assertIn(phrase, row["text"])


if __name__ == "__main__":
    unittest.main()
