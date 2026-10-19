#!/usr/bin/env python3
import argparse, json, math, os, shutil, zipfile
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.recordingPen import RecordingPen

WEIGHT_NAMES={100:'Thin',200:'ExtraLight',300:'Light',400:'Regular',500:'Medium',600:'SemiBold',700:'Bold',800:'ExtraBold',900:'Black'}
WIDTH_NAMES={62.5:'ExtraCondensed',75:'Condensed',87.5:'SemiCondensed',100:'Normal'}

def axes(font):
    if 'fvar' not in font: return []
    return [dict(tag=a.axisTag,min=float(a.minValue),default=float(a.defaultValue),max=float(a.maxValue)) for a in font['fvar'].axes]

def glyph_signature(font, name):
    gs=font.getGlyphSet(); pen=RecordingPen(); gs[name].draw(pen)
    ops=[]
    for op, pts in pen.value:
        ops.append((op,len(pts)))
    return ops

def report(font):
    glyphs=font.getGlyphOrder(); bad=[]
    # A single VF is internally compilable; report structural complexity useful for future multi-master comparisons.
    for g in glyphs:
        try: sig=glyph_signature(font,g)
        except Exception as e: bad.append({'glyph':g,'error':str(e)}); continue
        if not sig and g != '.notdef': pass
    return {'glyph_count':len(glyphs),'read_errors':bad,'status':'pass' if not bad else 'warning'}

def static_instance(src, dst, loc, slant=0.0):
    f=TTFont(src)
    f=instantiateVariableFont(f, loc, inplace=False, optimize=True)
    if slant:
        # TrueType glyf affine shear around baseline; update advance bounds naturally via outlines.
        if 'glyf' not in f: raise RuntimeError('Slant MVP currently supports TrueType glyf outlines only')
        k=math.tan(math.radians(slant))
        glyf=f['glyf']
        for name in f.getGlyphOrder():
            g=glyf[name]
            if g.isComposite():
                for c in g.components:
                    # shift component origins according to y; preserve component transforms
                    c.x = round(c.x + k*c.y)
            elif g.numberOfContours and hasattr(g,'coordinates'):
                coords=g.coordinates
                for i,(x,y) in enumerate(coords): coords[i]=(round(x+k*y),y)
        if 'post' in f: f['post'].italicAngle=-slant
        # hhea caret slope convention
        if 'hhea' in f:
            f['hhea'].caretSlopeRise=1000; f['hhea'].caretSlopeRun=round(math.tan(math.radians(slant))*1000)
    # remove variation tables for static export
    for t in ['fvar','gvar','avar','STAT','HVAR','MVAR']:
        if t in f: del f[t]
    f.save(dst)

def main():
    ap=argparse.ArgumentParser(description='Font Family Merger v3 foundation')
    ap.add_argument('font'); ap.add_argument('-o','--out',default='FontFamilyMerger-v3-output')
    ap.add_argument('--extract-matrix',action='store_true'); ap.add_argument('--slant',type=float,default=0)
    args=ap.parse_args(); src=Path(args.font); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    f=TTFont(src); ax=axes(f); meta={'source':src.name,'axes':ax,'compatibility':report(f)}
    (out/'report.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    shutil.copy2(src,out/src.name)
    # Designspace descriptor: references the VF as source; usable as project metadata and foundation for expanded sources.
    ds=['<?xml version="1.0" encoding="UTF-8"?>','<designspace format="5.0">','  <axes>']
    for a in ax:
        nm={'wght':'Weight','wdth':'Width','slnt':'Slant','opsz':'Optical Size'}.get(a['tag'],a['tag'])
        ds.append(f'    <axis tag="{a["tag"]}" name="{nm}" minimum="{a["min"]}" default="{a["default"]}" maximum="{a["max"]}"/>')
    ds += ['  </axes>','</designspace>']
    (out/'family.designspace').write_text('\n'.join(ds)+'\n',encoding='utf-8')
    if args.extract_matrix:
        d=out/'static-matrix'; d.mkdir(exist_ok=True)
        ranges={a['tag']:(a['min'],a['max']) for a in ax}
        widths=[v for v in WIDTH_NAMES if 'wdth' in ranges and ranges['wdth'][0]<=v<=ranges['wdth'][1]] or [100]
        weights=[v for v in WEIGHT_NAMES if 'wght' in ranges and ranges['wght'][0]<=v<=ranges['wght'][1]] or [400]
        for wd in widths:
            for wt in weights:
                loc={}
                if 'wdth' in ranges: loc['wdth']=wd
                if 'wght' in ranges: loc['wght']=wt
                prefix='' if wd==100 else WIDTH_NAMES[wd]
                style=(prefix+WEIGHT_NAMES[wt]) if prefix else WEIGHT_NAMES[wt]
                if args.slant: style += ('ReverseOblique' if args.slant<0 else 'Oblique')
                static_instance(src,d/f'{src.stem.split("-")[0]}-{style}.ttf',loc,args.slant)
    print(out.resolve())
if __name__=='__main__': main()