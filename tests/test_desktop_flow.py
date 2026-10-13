import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from app_test_support import OfflineAITestCase
ROOT=Path(__file__).resolve().parents[1]

class DesktopFlowTests(OfflineAITestCase):
    def app(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=15).run()
        for toggle in app.toggle:
            if toggle.value:toggle.set_value(False)
        app.run()
        return app

    def test_greeting_then_incremental_teaching_and_followup(self):
        app=self.app()
        app.chat_input[0].set_value('สวัสดีครับ').run()
        self.assertEqual(app.session_state['messages'][-1]['status'],'conversation')
        app.chat_input[0].set_value('Bubble Sort ทีละขั้น').run()
        self.assertFalse(app.exception)
        steps=app.session_state['messages'][-1]['evidence']
        self.assertGreaterEqual(len(steps),3)
        self.assertEqual(app.session_state['part-1'],0)
        next(b for b in app.button if b.label=='ส่วนถัดไป').click().run()
        self.assertEqual(app.session_state['part-1'],1)
        app.chat_input[0].set_value('แล้วความซับซ้อนล่ะ').run()
        self.assertFalse(app.exception)
        self.assertIn('bubble',app.session_state['messages'][-1]['query']['topics'])

    def test_english_source_is_preserved_when_translation_is_off(self):
        app=self.app()
        app.chat_input[0].set_value('Bubble Sort step by step').run()
        self.assertFalse(app.exception)
        result=app.session_state['messages'][-1]
        self.assertEqual(result['source_language'],'en')
        self.assertIn('In pass',result['answer'])

if __name__=='__main__':unittest.main()
