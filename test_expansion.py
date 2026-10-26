import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image
from build import ROLES,SIZES
import pixel

ROOT=Path(__file__).parent


class AllCharacterPixels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        groups=set(json.loads((ROOT/'release-policy.json').read_text())['active_groups'])
        cls.items=[x for x in json.loads((ROOT/'sources.json').read_text()) if x['available'] and x['group'] in groups]

    def test_all_19_have_unique_own_pixel_art(self):
        self.assertEqual(len(self.items),19)
        self.assertIn('taffy',{item['id'] for item in self.items})
        unique=set()
        for item in self.items:
            self.assertTrue(pixel.enabled(item),item['id'])
            unique.add(hashlib.sha256(pixel.pose(0,item).tobytes()).digest())
            self.assertTrue((ROOT/f'artwork/pixel-{item["id"]}/prompt.txt').exists())
        self.assertEqual(len(unique),19,'Do not recolour or reuse Diana as another character')

    def test_new_character_base_frames_are_real_small_grid_and_aligned(self):
        for item in self.items:
            if pixel.advanced(item):continue
            colors=set();frames=set()
            for frame in range(8):
                image=pixel.pose(frame,item)
                self.assertEqual(image.size,(48,48))
                self.assertEqual(image.getbbox()[3],47,item['id'])
                self.assertLessEqual(set(image.getchannel('A').getdata()),{0,255})
                colors.update(image.getdata());frames.add(image.tobytes())
            self.assertLessEqual(len(colors),32,item['id'])
            self.assertEqual(len(frames),8,item['id'])

    def test_all_character_native_roles_animate_without_moving_hotspot(self):
        for item in self.items:
            for role in ROLES:
                for size in SIZES:
                    images=[pixel.render(item,role,size,i) for i in range(8)]
                    self.assertEqual(len({hot for _,hot in images}),1,(item['id'],role))
                    self.assertGreater(len({im.tobytes() for im,_ in images}),1,(item['id'],role,size))

    def test_dedicated_keyframe_claim_only_for_diana(self):
        for item in self.items:
            if item['id']=='diana':continue
            self.assertFalse(pixel.advanced(item))
            self.assertEqual(set(pixel.behaviors(item)),set(ROLES))
            self.assertTrue(all('基础' in info['meaning'] for info in pixel.behaviors(item).values()))


if __name__=='__main__':unittest.main()
