"""Shared rounded, character-coloured pointer; the tip remains the hotspot."""
from PIL import Image, ImageDraw, ImageColor


def pointer(canvas, color, origin=(3, 3), pixel=False):
    scale = 8
    layer = Image.new('RGBA', (24 * scale, 28 * scale))
    draw = ImageDraw.Draw(layer)
    # A compact, softly curved silhouette, not a large white Windows arrow.
    path = [(0, 0), (0, 17), (.3, 18), (1, 18), (5.3, 14),
            (8.7, 21.5), (9.5, 22), (12, 20.8), (12.4, 20),
            (9, 12.8), (15, 12.5), (16, 12), (15.7, 11), (0, 0)]
    xy = [(round((x + 1) * scale), round((y + 1) * scale)) for x, y in path]
    rgb = ImageColor.getrgb(color)
    ink = tuple(round(v * .46) for v in rgb)
    draw.polygon(xy, fill=color)
    draw.line(xy, fill=ink, width=scale, joint='curve')
    for x, y in xy[1:-1]:
        draw.ellipse((x-scale//2,y-scale//2,x+scale//2,y+scale//2),fill=ink)
    draw.line([(3*scale,6*scale),(3*scale,13*scale)], fill=tuple(round(v*.45+255*.55) for v in rgb), width=scale)
    target = (24, 28) if pixel else (96, 112)
    layer = layer.resize(target, Image.Resampling.LANCZOS)
    if pixel:
        layer.putalpha(layer.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
    step = 1 if pixel else 4
    canvas.alpha_composite(layer, ((origin[0]-1)*step, (origin[1]-1)*step))
