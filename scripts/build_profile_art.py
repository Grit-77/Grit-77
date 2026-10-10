"""Compose Grit's current portrait with a fixed editorial header and frame loop.

No portrait retouching, rescaling, generated imagery, camera motion or text motion.
Requires Pillow, NumPy and native Times New Roman/Segoe UI or DejaVu fonts.
Usage: python scripts/build_profile_art.py --source assets/profile/portrait-source.png --output-dir assets/profile
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT, FRAMES, DURATION = 1200, 520, 120, 50
CREAM = (242, 238, 224)
INK = (28, 30, 26)
OLIVE = (176, 194, 127)
FRAME = (57, 61, 45)
PORTRAIT_X, PORTRAIT_Y = 720, 30
PANEL_X = 700
FRAME_BOX = (710, 20, 1190, 500)


def font_paths(directory=None):
    directories = [Path(directory)] if directory else [Path('C:/Windows/Fonts'),Path('/usr/share/fonts/truetype/dejavu')]
    for folder in directories:
        if (folder/'timesbd.ttf').exists():
            return folder/'timesbd.ttf', folder/'times.ttf', folder/'segoeuib.ttf'
        if (folder/'DejaVuSerif-Bold.ttf').exists():
            return folder/'DejaVuSerif-Bold.ttf', folder/'DejaVuSerif.ttf', folder/'DejaVuSans.ttf'
    raise SystemExit('Pass --font-dir with Times New Roman/Segoe UI or DejaVu fonts.')


def text_layer(fonts):
    layer = Image.new('RGBA',(WIDTH*2,HEIGHT*2))
    d=ImageDraw.Draw(layer)
    bold,serif,sans=fonts
    def text(x,y,copy,size,path,color=INK):
        d.text((x*2,y*2),copy,fill=(*color,255),font=ImageFont.truetype(str(path),size*2),anchor='lt')
    text(57,77,'İsmet Aydın',26,serif)
    text(50,149,'GRIT',232,bold)
    copy='AI SYSTEMS. CHECKED WORK.'
    f=ImageFont.truetype(str(sans),20*2)
    x=58*2
    for char in copy:
        # A shared baseline keeps punctuation below capitals when tracking glyphs.
        d.text((x,391*2),char,fill=(*INK,255),font=f,anchor='ls')
        x+=d.textlength(char,font=f)+2.25*2
    d.line(((58*2,420*2),(641*2,420*2)),fill=(174,178,153,255),width=2)
    return layer.resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)


def frame_point(distance):
    x0,y0,x1,y1=FRAME_BOX
    w,h=x1-x0,y1-y0
    distance%=2*(w+h)
    if distance<w:return x0+distance,y0
    distance-=w
    if distance<h:return x1,y0+distance
    distance-=h
    if distance<w:return x1-distance,y1
    return x0,y1-(distance-w)


def render(index,base):
    result=base.copy()
    d=ImageDraw.Draw(result)
    perimeter=2*((FRAME_BOX[2]-FRAME_BOX[0])+(FRAME_BOX[3]-FRAME_BOX[1]))
    head=index*perimeter/FRAMES
    length=72
    # Follow a closed path at constant speed. Frame pixels never overlap the portrait.
    points=[frame_point(head+i) for i in range(length+1)]
    d.line(points,fill=OLIVE,width=2)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--font-dir',type=Path)
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    with Image.open(args.source) as original:
        original.load()
        if original.size!=(460,460):raise SystemExit(f'Expected actual 460×460 avatar, got {original.size}.')
        portrait=original.convert('RGB')
    background=tuple(portrait.getpixel((0,0)))
    base=Image.new('RGB',(WIDTH,HEIGHT),CREAM)
    d=ImageDraw.Draw(base)
    d.rectangle((PANEL_X,0,WIDTH,HEIGHT),fill=background)
    d.rectangle(FRAME_BOX,outline=FRAME,width=1)
    base.paste(portrait,(PORTRAIT_X,PORTRAIT_Y))
    base=Image.alpha_composite(base.convert('RGBA'),text_layer(font_paths(args.font_dir))).convert('RGB')
    raw_frames=[render(i,base) for i in range(FRAMES)]
    # Most pixels remain fixed, so one full representative frame creates the palette.
    # No dithering: halftone illustration already contains its own deliberate texture.
    palette=raw_frames[0].quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    frames=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in raw_frames]
    gif_path=args.output_dir/'grit-portrait-loop.gif'
    png_path=args.output_dir/'grit-portrait-cover.png'
    raw_frames[0].save(png_path,optimize=True)
    frames[0].save(gif_path,save_all=True,append_images=frames[1:],duration=DURATION,loop=0,disposal=1,optimize=True)
    shutil.copyfile(args.source,args.output_dir/'portrait-source.png')
    source_region=(PORTRAIT_X,PORTRAIT_Y,PORTRAIT_X+460,PORTRAIT_Y+460)
    assert raw_frames[0].crop(source_region).tobytes()==portrait.tobytes()
    decoded=[]
    durations=[]
    with Image.open(gif_path) as gif:
        loop=gif.info.get('loop')
        assert gif.n_frames==FRAMES and gif.size==(WIDTH,HEIGHT)
        for i in range(gif.n_frames):
            gif.seek(i)
            frame=gif.convert('RGB')
            decoded.append(np.asarray(frame,dtype=np.int16))
            durations.append(gif.info.get('duration',0))
            if i in (0,30,60,90,119):frame.save(args.output_dir/f'frame-{i:03}.png')
    adj=[np.abs(decoded[i+1]-decoded[i]) for i in range(FRAMES-1)]
    means=[float(delta.mean()) for delta in adj]
    seam=np.abs(decoded[0]-decoded[-1])
    fixed=np.ones((HEIGHT,WIDTH),dtype=bool)
    fixed[18:503,708:1193]=False
    fixed_max=max(int(delta[fixed].max()) for delta in adj)
    portrait_max=max(int(delta[PORTRAIT_Y:PORTRAIT_Y+460,PORTRAIT_X:PORTRAIT_X+460].max()) for delta in adj)
    stats={
        'dimensions':[WIDTH,HEIGHT],'frames':FRAMES,'duration_ms':sum(durations),'frame_durations_ms':sorted(set(durations)),
        'loop':loop,'gif_bytes':gif_path.stat().st_size,'png_bytes':png_path.stat().st_size,
        'source_dimensions':[460,460],'source_file_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'source_copied_byte_for_byte':(args.output_dir/'portrait-source.png').read_bytes()==args.source.read_bytes(),
        'static_portrait_rgb_identical_to_source':raw_frames[0].crop(source_region).tobytes()==portrait.tobytes(),
        'decoded_portrait_adjacent_max_rgb_delta':portrait_max,'fixed_background_and_type_adjacent_max_rgb_delta':fixed_max,
        'seam_mean_absolute_rgb_delta':float(seam.mean()),'seam_max_rgb_delta':int(seam.max()),
        'adjacent_mean_delta_min':min(means),'adjacent_mean_delta_median':float(np.median(means)),'adjacent_mean_delta_max':max(means),
        'adjacent_max_rgb_delta':max(int(delta.max()) for delta in adj),
        'all_frames_decoded':True,'palette':'one shared 256-color palette; no added dithering',
        'gif':str(gif_path),'static_cover':str(png_path),
        'limitations':['GIF uses fixed color quantization; source/PNG portrait retain exact source pixels.', 'Parent reviews actual GitHub rendering/reduced-motion source selection before publication.']
    }
    assert loop==0 and durations==[DURATION]*FRAMES
    assert fixed_max==0 and portrait_max==0
    assert float(seam.mean())<=max(means)*1.25
    assert gif_path.stat().st_size<=2_000_000
    (args.output_dir.parent/'checks.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    print(json.dumps(stats,indent=2))


if __name__=='__main__':main()
