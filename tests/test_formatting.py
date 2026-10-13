import unittest
from services import formatting

class FormattingTests(unittest.TestCase):
    def test_ai_can_only_insert_breaks_and_bullets_preserving_every_source_character(self):
        source='Bubble Sort compares 10 and 20. รอบสอง สลับ 30 กับ 40'
        result=formatting.format_passages([source],generate=lambda _: {'layouts':[{'break_before':['รอบสอง สลับ'],'bullet':True}]})
        self.assertEqual(result,['• Bubble Sort compares 10 and 20. \n• รอบสอง สลับ 30 กับ 40'])

    def test_invalid_anchor_reordering_duplicate_and_word_splits_fall_back(self):
        source='First 10. Second 20. Third 30.'
        for anchors in [['Changed 10'],['Third 30.','Second 20.'],['Second 20.','Second 20.'],['irst 10.']]:
            with self.subTest(anchors=anchors):
                result=formatting.format_passages([source],generate=lambda _,a=anchors:{'layouts':[{'break_before':a,'bullet':True}]})
                self.assertEqual(result,[source])
        self.assertEqual(formatting.format_passages(['one one'],generate=lambda _:{'layouts':[{'break_before':['one'],'bullet':True}]}),['one one'])

    def test_malformed_output_and_provider_failure_keep_all_passages(self):
        sources=['A[1] = 10\nB = 20','ข้อความเดิม']
        for value in [None,{}, {'layouts':[]}, {'layouts':[{'break_before':[],'bullet':'yes'},{}]}]:
            self.assertEqual(formatting.format_passages(sources,generate=lambda _,v=value:v),sources)
        def unavailable(_):raise ValueError('unavailable')
        self.assertEqual(formatting.format_passages(sources,generate=unavailable),sources)

    def test_existing_multiline_code_and_tables_are_not_reformatted(self):
        source='for i = 1 to n\n    A[i] = A[i-1]\n    return A'
        self.assertEqual(formatting.format_passages([source],generate=lambda _:{'layouts':[{'break_before':['A[i] ='],'bullet':True}]}),[source])


class ManualFormattingTests(unittest.TestCase):
    def test_manual_layout_preserves_source_and_never_calls_ai(self):
        self.assertEqual(formatting.manual_layout('One 10.\n\nTwo 20.'),'• One 10.\n\n• Two 20.')
        self.assertEqual(formatting.manual_layout('A[i] = 10\nreturn A'),'A[i] = 10\nreturn A')

    def test_accepts_ai_array_layout_without_accepting_replacement_text(self):
        self.assertEqual(formatting.format_passages(['First 10. Second 20.'],generate=lambda _:[{'break_before':['Second 20.'],'bullet':True}]),['• First 10. \n• Second 20.'])
        self.assertEqual(formatting.format_passages(['First 10.'],generate=lambda _:{'layouts':[{'break_before':[],'bullet':True,'text':'First 99.'}]}),['First 10.'])

class ReadingLayoutTests(unittest.TestCase):
    def test_bubble_trace_separates_input_actions_result_and_counts_without_changing_content(self):
        source='ทำตาม รุ่น หยุด ก่อน จาก ซ้าย ไป ขวา\nเริ่ม  [5,1,4,2,8]  รอบ แรก สลับ  (5,1),  (5,4),  (5,2)  และ ไม่ สลับ  (5,8)  ได้  [1,4,2,5,8]  เปรียบเทียบ สี่ และ สลับ สาม\nครั้ง  ขอบ ขวา ใหม่ ไม่ นับ  8'
        blocks=formatting.reading_blocks(formatting.manual_layout(source))
        self.assertEqual(blocks,[
            'ทำตามรุ่นหยุดก่อนจากซ้ายไปขวา',
            'เริ่ม [5,1,4,2,8]',
            'รอบแรกสลับ (5,1), (5,4), (5,2) และไม่สลับ (5,8)',
            'ได้ [1,4,2,5,8]',
            'เปรียบเทียบสี่และสลับสามครั้งขอบขวาใหม่ไม่นับ 8'])
        import re
        self.assertEqual(re.sub(r'\s','', ''.join(blocks)),re.sub(r'\s','',source))

    def test_english_words_and_code_indentation_remain_intact(self):
        self.assertEqual(formatting.reading_blocks('• In pass 1, compare 5 and 1.\nThen swap.'),['In pass 1, compare 5 and 1. Then swap.'])
        code='for i = 1 to n\n    A[i] = A[i-1]'
        self.assertEqual(formatting.reading_blocks(code),[code])

    def test_ai_cannot_detach_count_units_into_a_separate_paragraph(self):
        source='เปรียบเทียบ สี่ และ สลับ สาม\nครั้ง ขอบ ขวา ใหม่'
        output=formatting.format_passages([source],generate=lambda _:{'layouts':[{'break_before':['ครั้ง ขอบ'],'bullet':True}]})
        self.assertEqual(output,[source])

    def test_display_rejects_any_added_missing_or_reordered_content(self):
        for layout in ['• เริ่ม [9,1]','• เริ่ม','• [5,1] เริ่ม']:
            self.assertEqual(formatting.reading_blocks(layout,source='เริ่ม [5,1]'),['เริ่ม [5,1]'])

    def test_existing_source_bullet_is_not_mistaken_for_a_generated_marker(self):
        source='• ข้อ เดิม'
        self.assertEqual(formatting.reading_blocks(source,source=source),['• ข้อเดิม'])

    def test_view_escapes_source_markup_and_emphasizes_only_existing_arrays(self):
        from ui.reading_view import reading_html
        html=reading_html(['เริ่ม [5,1,4,2,8]','<script>alert(1)</script>'])
        self.assertIn('<code>[5,1,4,2,8]</code>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>',html)

    def test_prose_with_a_variable_or_for_example_is_not_a_code_block(self):
        from ui.reading_view import reading_html
        for source in ['กำหนด m=i ก่อนเริ่มรอบใหม่','For example, compare the next two records.']:
            rendered=reading_html([source])
            self.assertNotIn('<pre>',rendered)
            self.assertIn('<p>',rendered)

if __name__=='__main__':unittest.main()
