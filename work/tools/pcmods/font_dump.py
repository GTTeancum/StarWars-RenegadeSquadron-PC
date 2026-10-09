r"""Decodes the game's fonts (GRAPHICS\FONTS.ASR): FONT chunks per Asura_Chunk_Font
version 3 and the glyph pages stored as PSP IDX8 textures with an 8888 CLUT
(Asura_PSP_TextureManagement::Load order: pixels then CLUT, linear when flags=0)."""
import struct, sys, json
from PIL import Image
GAME=r'C:\Games\Star Wars Renegade Squadron\data\PSP_GAME\USRDIR'
b=open(GAME+r'\GRAPHICS\FONTS.ASR','rb').read()
p=8; textures={}; fonts=[]
while p+16<=len(b):
    tag=b[p:p+4].decode('latin1'); size,ver,flags=struct.unpack_from('<III',b,p+4)
    if tag=='RSCF':
        t,unk,dsz=struct.unpack_from('<III',b,p+16); q=p+28; name=b[q:b.index(b'\0',q)].decode(); q=b.index(b'\0',q)+1
        while q%4: q+=1
        w,h,fl,fmt,mips=struct.unpack_from('<HHHBB',b,q); q+=8
        assert fmt==5 and fl==0, (fmt,fl)
        pix=b[q:q+w*h]; clut=b[q+w*h:q+w*h+1024]
        pal=[struct.unpack_from('<I',clut,i*4)[0] for i in range(256)]
        img=Image.new('RGBA',(w,h)); px=img.load()
        for y in range(h):
            for x in range(w):
                c=pal[pix[y*w+x]]; px[x,y]=(c&255,(c>>8)&255,(c>>16)&255,(c>>24)&255)
        textures[name.lower().split(chr(92))[-1]]=img
    elif tag=='FONT':
        q=p+16; fname=b[q:q+100].split(b'\0')[0].decode(); q+=100
        height,npages=struct.unpack_from('<fI',b,q); q+=8
        f={'name':fname,'height':height,'pages':[]}
        for _ in range(npages):
            tex=b[q:q+100].split(b'\0')[0].decode(); q+=100
            idx,ptr,rmin,rmax,tw,th,nchars=struct.unpack_from('<iiHHIII',b,q); q+=24
            glyphs=[struct.unpack_from('<fffHH',b,q+i*16) for i in range(nchars)]; q+=nchars*16
            f['pages'].append({'texture':tex,'range':(rmin,rmax),'size':(tw,th),'glyphs':glyphs})
        fonts.append(f)
    p+=size
for f in fonts:
    print(f['name'],'height',f['height'])
    for pg in f['pages']:
        print('  page',pg['texture'],pg['range'],pg['size'],len(pg['glyphs']),'glyphs; sample',[(round(u,3),round(v,3),round(w,2),chr(c) if 32<=c<127 else c,k) for u,v,w,c,k in pg['glyphs'][33:38]])
for n,img in textures.items(): print('texture',n,img.size); img.save(sys.argv[1]+'\\'+n.split('\\')[-1].replace('.tga','.png'))
# render a sample line with the 13 font
f=fonts[0]; pg=f['pages'][0]; tex=textures[pg['texture'].lower().split(chr(92))[-1]]
gl={c:(u,v,w) for u,v,w,c,k in pg['glyphs']}
text='Video Options 1280x720'; H=f['height']; x=0; out=Image.new('RGBA',(400,int(H)+4),(30,30,60,255))
for ch in text:
    if ord(ch) not in gl: x+=4; continue
    u,v,w=gl[ord(ch)]; src=tex.crop((int(u*tex.width),int(v*tex.height),int(u*tex.width+w*tex.width) if w<1 else int(u*tex.width+w),int(v*tex.height+H)))
    out.alpha_composite(src,(x,2)); x+=src.width
out.save(sys.argv[1]+r'\font-sample.png'); print('glyph width units: first glyph w',pg['glyphs'][33][2])
