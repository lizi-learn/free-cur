import json
import unittest
from pathlib import Path
from PIL import Image, ImageColor
from cursor_style import pointer
from build import artwork
import pixel


class RoundedStyleTests(unittest.TestCase):
    def test_all_current_characters_get_their_own_arrow_colour(self):
        root=Path(__file__).parent
        groups=set(json.loads((root/'release-policy.json').read_text())['active_groups'])
        items=[x for x in json.loads((root/'sources.json').read_text()) if x['available'] and x['group'] in groups]
        self.assertEqual(len(items),19)
        for item in items:
            image,hot=artwork(item,'Arrow',64)
            expected=ImageColor.getrgb(item['color'])
            region=image.crop((0,0,18,23)) if item['id']=='diana' else image.crop((2,2,20,25))
            self.assertTrue(any(a>200 and sum(abs(c-d) for c,d in zip((r,g,b),expected))<40 for r,g,b,a in region.getdata()),item['id'])
            self.assertTrue(image.getpixel(hot)[3]>0,item['id'])

    def test_compact_arrow_leaves_more_room_for_character(self):
        image=Image.new('RGBA',(64,64));pointer(image,'#ee8d9a',pixel=True,origin=(1,1))
        self.assertLessEqual(image.getbbox()[2],18)
        self.assertLessEqual(image.getbbox()[3],24)
        self.assertEqual(set(image.getchannel('A').getdata()),{0,255})

    def test_character_is_larger_but_not_clipped(self):
        for role in pixel.POSES:
            for frame in range(8):
                box=pixel.character_layer(role,frame).getbbox()
                self.assertLess(box[2],64)
                self.assertLess(box[3],64)


if __name__=='__main__':unittest.main()
