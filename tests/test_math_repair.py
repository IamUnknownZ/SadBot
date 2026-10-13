import unittest
from pathlib import Path
import pymupdf

ROOT=Path(__file__).resolve().parents[1]


class MathRepairTests(unittest.TestCase):
    def test_verified_font_recovery_preserves_raw_text_and_geometry(self):
        from services.math_repair import VerifiedMathDecoder
        with pymupdf.open(ROOT/'book_data/Cormen_Basic_Sorting_100_Pages.pdf') as pdf:
            decoder=VerifiedMathDecoder(pdf,ROOT/'metadata/math_glyph_map.json')
            page=pdf[6]
            blocks=decoder.blocks(page)
            rows=[line for block in blocks for line in block.get('lines',[])]
            repaired='\n'.join(''.join(s['text'] for s in line['spans']) for line in rows)
            raw='\n'.join(''.join(s['raw_text'] for s in line['spans']) for line in rows)
            self.assertIn('c₁n²',repaired)
            self.assertIn('c1n2',raw)
            self.assertIn('=',repaired)
            self.assertNotIn('\x01',repaired)
            self.assertTrue(all('bbox' in s for l in rows for s in l['spans']))

    def test_math_symbols_are_decoded_from_glyph_not_globally_replaced(self):
        from services.math_repair import VerifiedMathDecoder
        with pymupdf.open(ROOT/'book_data/Cormen_Basic_Sorting_100_Pages.pdf') as pdf:
            decoder=VerifiedMathDecoder(pdf,ROOT/'metadata/math_glyph_map.json')
            self.assertEqual(decoder.glyph('MT2SYT',8,'D'),'=')
            self.assertEqual(decoder.glyph('MT2MIT',18,'D'),'D')
            self.assertEqual(decoder.glyph('TimesNewRoman',0,'D'),'D')
            self.assertEqual(decoder.glyph('MT2MIT',73,'Œ'),'[')
            self.assertEqual(decoder.glyph('MT2MIT',70,'‚'),'Θ')

    def test_source_hash_mismatch_does_not_apply_the_custom_mapping(self):
        from services.math_repair import VerifiedMathDecoder
        with pymupdf.open() as pdf:
            pdf.new_page().insert_text((50,50),'D C 123')
            decoder=VerifiedMathDecoder(pdf,ROOT/'metadata/math_glyph_map.json')
            self.assertFalse(decoder.enabled)
            self.assertEqual(decoder.glyph('MT2SYT',8,'D'),'D')


if __name__=='__main__':unittest.main()
