import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from app_test_support import OfflineAITestCase
ROOT=Path(__file__).resolve().parents[1]

class EvidenceDialogTests(OfflineAITestCase):
    def app(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
        app.toggle[0].set_value(False).run()
        return app

    def test_evidence_is_loaded_only_when_requested_and_closes_without_losing_answer(self):
        app=self.app()
        app.chat_input[0].set_value('Bubble Sort ทีละขั้น').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('component_instance')),0)
        self.assertNotIn('เปิดดูหลักฐาน',[h.value for h in app.subheader])
        next(b for b in app.button if b.label.startswith('ดูหลักฐาน')).click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('component_instance')),1)
        next(b for b in app.button if b.label=='กลับไปอ่านคำตอบ').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('component_instance')),0)
        self.assertEqual(app.session_state['messages'][-1]['status'],'answered')
        self.assertEqual(app.session_state['part-0'],0)

    def test_greeting_uses_plain_chat_text_instead_of_nested_alert_frame(self):
        app=self.app()
        app.chat_input[0].set_value('Hello').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.info),0)
        self.assertEqual(app.session_state['messages'][-1]['status'],'conversation')

    def test_evidence_header_metadata_has_three_compact_rows(self):
        app=self.app()
        app.chat_input[0].set_value('Bubble Sort ทีละขั้น').run()
        next(b for b in app.button if b.label.startswith('ดูหลักฐาน')).click().run()
        captions=[c.value for c in app.caption]
        document=[value for value in captions if value.startswith('Basic Sorting Algorithms')]
        page=[value for value in captions if value.startswith('หน้า PDF ')]
        self.assertEqual(len(document),1)
        self.assertNotIn('หน้า PDF',document[0])
        self.assertEqual(len(page),1)
        self.assertIn('บรรทัด',page[0])
        css='\n'.join(m.value for m in app.markdown if 'evidence-popup-meta' in m.value)
        self.assertIn('font-size:.72rem!important;line-height:1!important',css)

    def test_evidence_close_button_uses_title_baseline_offset(self):
        app=self.app()
        css='\n'.join(m.value for m in app.markdown if 'evidence-popup' in m.value)
        close_rule=css.split('.st-key-evidence-popup .st-key-close-evidence-popup button{',1)[1].split('}',1)[0]
        self.assertIn('transform:translateY(5px)',close_rule)

if __name__=='__main__':unittest.main()
