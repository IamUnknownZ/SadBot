import unittest
from pathlib import Path
from services.ingest import load_dataset
from services.answering import answer

ROOT=Path(__file__).resolve().parents[1]
class LiveDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=load_dataset(ROOT)

    def test_arithmetic_example_is_not_silently_answered_from_sorting_book(self):
        self.assertEqual(answer('10 คูณ 10 ทำไมเท่ากับ 100',self.data,ROOT)['status'],'insufficient_evidence')

    def test_basic_bubble_definition_does_not_show_an_opposite_direction_trace(self):
        result=answer('Bubble Sort คืออะไร',self.data,ROOT)
        self.assertIn('left to right',result['answer'])
        self.assertIsNone(result['image'])

    def test_optional_image_links_to_actual_evidence_without_removing_other_text(self):
        result=answer('อธิบาย Bubble Sort',self.data,ROOT)
        self.assertEqual(result['status'],'answered')
        self.assertTrue({c['id'] for c in result['evidence']}.intersection(result['image']['linked_chunk_ids']))
        self.assertNotIn('เนื้อหา อธิบาย เพิ่มเติม',result['answer'])

    def test_step_request_returns_an_actual_worked_trace(self):
        result=answer('Bubble Sort ทีละขั้น',self.data,ROOT)
        self.assertEqual(result['status'],'answered')
        self.assertIn('[5,1,4,2,8]',result['answer'])
        self.assertIn('[1,2,4,5,8]',result['answer'])

if __name__=='__main__':unittest.main()

class IntentSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=load_dataset(ROOT)

    def test_generic_insertion_explanation_uses_key_insertion_not_hybrid_sorting(self):
        result=answer('Insertion Sort ทำงานอย่างไร',self.data,ROOT)
        self.assertEqual(result['status'],'answered')
        self.assertIn(result['image']['page'],[55,56,67,68,69,70,71])

    def test_counting_steps_use_counting_phases_not_range_count_queries(self):
        result=answer('Counting Sort ขั้นตอน',self.data,ROOT)
        self.assertEqual(result['status'],'answered')
        self.assertEqual(result['image']['page'],95)

    def test_merge_time_explanation_has_a_matching_cost_image(self):
        result=answer('ทำไม Merge Sort ใช้เวลา n log n',self.data,ROOT)
        self.assertEqual(result['status'],'answered')
        self.assertEqual(result['image']['page'],85)

class UnsupportedDetailsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=load_dataset(ROOT)

    def test_new_array_is_not_mistaken_for_the_books_worked_example(self):
        self.assertEqual(answer('Bubble Sort เรียง [9,7,4] ให้หน่อย',self.data,ROOT)['status'],'insufficient_evidence')

    def test_authorship_question_does_not_return_algorithm_steps(self):
        self.assertEqual(answer('ผู้แต่ง Bubble Sort คือใคร',self.data,ROOT)['status'],'insufficient_evidence')

class EvidenceImageFallbackTests(unittest.TestCase):
    def test_selection_uses_real_figure_without_paragraph_screenshot(self):
        data=load_dataset(ROOT)
        result=answer('Selection Sort ทำงานอย่างไร',data,ROOT)
        self.assertEqual(result['status'],'answered')
        self.assertEqual(result['image']['image_type'],'visual_explanation')
        self.assertIn(result['image']['kind'],['diagram','flowchart','chart','table_image','figure'])
