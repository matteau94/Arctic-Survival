import re
src='C:/Users/leosp/.claude/projects/C--Users-leosp-Documents-Blender-Artic-Survival/7bb4c7a2-2c8e-4793-b5ee-2fc544b80253/tool-results/pdfstreams.txt'
t=open(src,'rb').read().decode('latin1')
lines=[]
for blk in re.findall(r'BT(.*?)ET',t,re.S):
    s=''
    for m in re.finditer(r'\[(.*?)\]\s*TJ|\((.*?)\)\s*Tj',blk,re.S):
        if m.group(1) is not None:
            for p in re.findall(r'\(((?:\.|[^\)])*)\)|(-?\d+\.?\d*)',m.group(1)):
                if p[0]: s+=p[0]
                elif p[1] and float(p[1])<-200: s+=' '
        else: s+=m.group(2)
    lines.append(s)
open('pdftext.txt','w',encoding='utf8').write('\n'.join(lines))
print("n",len(lines))
