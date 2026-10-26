import hashlib
import unittest
from PIL import Image
import pixel
from build import ROLES, SIZES, ani, cur
from verify import check_ani


class PixelCharacter(unittest.TestCase):
    def test_eight_distinct_poses_are_small_grid_and_transparent(self):
        hashes=set()
        for i in range(8):
            image=pixel.pose(i)
            self.assertEqual(image.size,(48,48))
            self.assertLessEqual(len(image.getcolors(4096)),32)
            self.assertLessEqual(set(image.getchannel('A').getdata()),{0,255})
            hashes.add(hashlib.sha256(image.tobytes()).digest())
        self.assertEqual(len(hashes),8)

    def test_all_roles_have_real_character_animation_and_stable_hotspots(self):
        for role in ROLES:
            for size in SIZES:
                images=[pixel.render({'id':'diana'},role,size,i) for i in range(8)]
                self.assertEqual(len({hot for im,hot in images}),1)
                self.assertGreater(len({im.tobytes() for im,hot in images}),1)
                for im,hot in images:
                    self.assertTrue(0<=hot[0]<size and 0<=hot[1]<size)
                    self.assertLessEqual(set(im.getchannel('A').getdata()),{0,255})

    def test_animated_windows_package_has_eight_multi_size_frames(self):
        frames=[cur([pixel.render({'id':'diana'},'Arrow',size,i) for size in SIZES]) for i in range(8)]
        check_ani(ani(frames,pixel.FRAME_MS))

    def test_moods_reference_real_pose_indices(self):
        for sequence in list(pixel.MOODS.values())+list(pixel.POSES.values()):
            self.assertEqual(len(sequence),8)
            self.assertTrue(all(0<=i<8 for i in sequence))

    def test_every_role_has_its_own_character_motion_not_just_different_badge(self):
        sequences={tuple(pixel.character_layer(role,i).tobytes() for i in range(8)) for role in ROLES}
        self.assertEqual(len(sequences),len(ROLES))
        self.assertEqual(set(pixel.BEHAVIORS),set(ROLES))
        self.assertEqual(set(pixel.MOTION),set(ROLES))

    def test_precision_text_and_wait_do_not_bounce(self):
        for role in ('IBeam','Crosshair','Wait'):
            self.assertEqual(set(pixel.MOTION[role]),{(0,0)})

    def test_resize_motion_matches_axis(self):
        self.assertTrue(all(x==0 for x,y in pixel.MOTION['SizeNS']))
        self.assertTrue(all(y==0 for x,y in pixel.MOTION['SizeWE']))
        self.assertTrue(all(x==y for x,y in pixel.MOTION['SizeNWSE']))
        self.assertTrue(all(x==-y for x,y in pixel.MOTION['SizeNESW']))

    def test_new_task_frames_have_shared_palette_and_ground_anchor(self):
        colors=set()
        for role in pixel.TASK_ROLES:
            frames=[]
            for i in range(4):
                image=Image.open(pixel.ROOT/f'artwork/pixel-diana-v2/{role}/{i}.png').convert('RGBA')
                self.assertEqual(image.size,(48,48))
                self.assertEqual(image.getbbox()[3],47)
                self.assertLessEqual(set(image.getchannel('A').getdata()),{0,255})
                opaque={(x,y) for y in range(48) for x in range(48) if image.getpixel((x,y))[3]}
                connected={next(iter(opaque))};queue=list(connected)
                for x,y in queue:
                    for dx in (-1,0,1):
                        for dy in (-1,0,1):
                            point=(x+dx,y+dy)
                            if point in opaque and point not in connected:connected.add(point);queue.append(point)
                self.assertEqual(connected,opaque,'No disconnected neighboring-cell fragments')
                colors.update(image.getdata());frames.append(image.tobytes())
            self.assertGreaterEqual(len(set(frames)),3)
        self.assertLessEqual(len(colors),32)

    def test_semantic_timing_is_slower_for_waiting_than_writing(self):
        self.assertGreater(pixel.DURATIONS['Wait'],pixel.DURATIONS['NWPen'])
        self.assertGreater(pixel.DURATIONS['IBeam'],pixel.DURATIONS['Hand'])
        self.assertTrue(all(ms*60%1000==0 for ms in pixel.DURATIONS.values()))


if __name__=='__main__':unittest.main()
