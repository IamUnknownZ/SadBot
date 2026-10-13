import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from app_test_support import OfflineAITestCase
ROOT=Path(__file__).resolve().parents[1]

class EnglishUITests(OfflineAITestCase):
    def test_efficiency_without_image_shows_all_source_without_unneeded_parts(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        for t in app.toggle:t.set_value(False)
        app.run()
        app.chat_input[0].set_value('ประสิทธิภาพ').run()
        self.assertFalse(app.exception)
        m=app.session_state['messages'][-1]
        self.assertEqual(m['source_language'],'en')
        self.assertEqual({e['page'] for e in m['evidence']},{7,8})
        self.assertIsNone(m['image'])
        self.assertTrue(any(b.label.startswith('ดูหลักฐาน') for b in app.button))
        self.assertFalse(any(b.label in ('ส่วนก่อนหน้า','ส่วนถัดไป') for b in app.button))
        next(b for b in app.button if b.label.startswith('ดูหลักฐาน · หน้า 8')).click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('component_instance')),1)
        next(b for b in app.button if b.label=='กลับไปอ่านคำตอบ').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(m['answer'],app.session_state['messages'][-1]['answer'])

    def test_welcome_and_greeting_stay_simple(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        for t in app.toggle:t.set_value(False)
        app.run();app.chat_input[0].set_value('ไง').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['messages'][-1]['status'],'conversation')
        self.assertEqual(len(app.info),0)

    def test_english_is_default_and_ai_selection_has_no_user_toggle(self):
        from unittest.mock import patch
        with patch.dict('os.environ',{'GEMINI_API_KEY':'test-key'}):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.toggle),1)
        self.assertFalse(app.toggle[0].value)

    def test_source_pseudocode_stays_indented_in_a_labeled_code_block(self):
        from services.ingest import load_dataset
        data=load_dataset(ROOT)
        original=next(c for c in data['chunks'] if c['text'].startswith('STABLE-SELECTION(A)'))
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        for toggle in app.toggle:toggle.set_value(False)
        app.run()
        app.chat_input[0].set_value('STABLE-SELECTION(A)').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(c.value==original['text'] for c in app.code))
        self.assertTrue(any(c.value=='รหัสเทียม · คงโค้ดต้นฉบับ' for c in app.caption))
        self.assertIn('        A[j] = A[j-1]',next(c.value for c in app.code if 'STABLE-SELECTION(A)' in c.value))

    def test_labels_inside_a_linked_figure_are_not_repeated_as_code(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        for toggle in app.toggle:toggle.set_value(False)
        app.run()
        app.chat_input[0].set_value('Mapping other domains').run()
        self.assertFalse(app.exception)
        message=app.session_state['messages'][-1]
        labels=[e for e in message['evidence'] if 'domain\n0\n1\n2\n3\n4\n5' in e['text']
                or 'R = 6 possible values; n = 8 records' in e['text']]
        self.assertTrue(labels)
        self.assertTrue(all(e['kind']=='figure_label' for e in labels))
        self.assertTrue(app.image)
        self.assertFalse(any('domain' in c.value or 'R = 6 possible values' in c.value for c in app.code))
        self.assertFalse(any('R = 6 possible values' in block.value for block in app.markdown))

    def test_hidden_figure_labels_do_not_show_untranslated_text_notices(self):
        from unittest.mock import patch
        def keep_native_labels(rows,**kwargs):
            return {r['id']:dict(text=r['text'],translated=r.get('kind')!='figure_label') for r in rows}
        with patch.dict('os.environ',{'GEMINI_API_KEY':'test-key'}), \
             patch('services.translation.translate_passages',side_effect=keep_native_labels):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
            app.toggle[0].set_value(True).run()
            app.chat_input[0].set_value('Mapping other domains').run()
        self.assertFalse(app.exception)
        self.assertTrue(app.image)
        self.assertFalse(any(c.value.startswith('คงข้อความต้นฉบับส่วนนี้') for c in app.caption))

    def test_selection_typo_and_correct_spelling_stay_short_even_without_ai(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        for toggle in app.toggle:toggle.set_value(False)
        app.run()
        for query in ['selecion sort','selection sort']:
            app.chat_input[0].set_value(query).run()
            self.assertFalse(app.exception)
            message=app.session_state['messages'][-1]
            self.assertEqual(message['query']['original'],query)
            self.assertEqual({e['page'] for e in message['evidence']},{46})
            self.assertLessEqual(len(message['evidence']),3)
        self.assertFalse(any('ส่วนที่ 1 จาก' in c.value for c in app.caption))

    def test_definition_displays_thai_prose_without_english_heading_clutter(self):
        from unittest.mock import patch
        def translator(rows,**kwargs):
            return {r['id']:dict(text='Bubble Sort คืออัลกอริทึมการเรียงลำดับ โดยสลับสมาชิกที่อยู่ติดกันและเรียงลำดับผิดซ้ำ ๆ',translated=True) for r in rows}
        with patch('services.translation.translate_passages',side_effect=translator):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
            app.toggle[0].set_value(True).run()
            app.chat_input[0].set_value('bubble sort คือ อะไร').run()
        self.assertFalse(app.exception)
        message=app.session_state['messages'][-1]
        self.assertEqual([e['page'] for e in message['evidence']],[34,36,36])
        self.assertEqual(message['retrieval_method'],'llm_selected_with_definition')
        self.assertTrue(any('สลับสมาชิกที่อยู่ติดกัน' in m.value for m in app.markdown))
        self.assertFalse(any('**S2.' in m.value or '**Correctness' in m.value for m in app.markdown))

    def test_ai_selector_is_used_for_a_different_algorithm_in_the_real_submit_flow(self):
        import json
        from unittest.mock import patch
        calls=[]
        def select(prompt):
            payload=json.loads(prompt);calls.append(payload)
            if 'catalog' in payload:
                return dict(mode='direct',search_query='What is selection sort?',section_id=None)
            row=next(r for r in payload['candidates'] if r['page']==46 and any('Selection sort divides' in l['text'] for l in r['lines']))
            return dict(intent='definition',selections=[dict(id=row['id'],first_line=row['lines'][0]['id'],last_line=row['lines'][-1]['id'])])
        def translate(rows,**kwargs):return {r['id']:dict(text='การเรียงลำดับแบบเลือกจะค้นหาค่าที่น้อยที่สุดจากส่วนที่ยังไม่เรียง',translated=True) for r in rows}
        with patch.dict('os.environ',{'GEMINI_API_KEY':'test-key'}),patch('services.conversation.generation_provider',return_value=select),patch('services.translation.translate_passages',side_effect=translate):
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
            app.chat_input[0].set_value('Selection Sort คืออะไร').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(calls),2)
        message=app.session_state['messages'][-1]
        self.assertEqual(message['selection_state'],'selected')
        self.assertEqual(message['query']['original'],'Selection Sort คืออะไร')
        self.assertEqual({e['page'] for e in message['evidence']},{46})

if __name__=='__main__':unittest.main()
