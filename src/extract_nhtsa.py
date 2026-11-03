# -*- coding: utf-8 -*-
"""STEP 0. NHTSA FLAT_CMPL.txt(1.6GB)에서 대상군·대조군 행만 추출 (로컬/Colab 공통, 약 10초)
사용: python extract_nhtsa.py FLAT_CMPL.txt  → hk.tsv.gz(현대·기아·제네시스), peer.tsv.gz(대조군)
배터리 적용 시 MAKES_TARGET / PEERS 만 바꾸면 됨"""
import sys, gzip
MAKES_TARGET = {'HYUNDAI', 'KIA', 'GENESIS'}
PEERS = {'TOYOTA': ['CAMRY', 'RAV4', 'HIGHLANDER'], 'HONDA': ['ACCORD', 'CR-V', 'PILOT'], 'NISSAN': ['ALTIMA', 'ROGUE', 'MURANO', 'LEAF'],
         'FORD': ['FUSION', 'ESCAPE', 'EDGE'], 'CHEVROLET': ['MALIBU', 'EQUINOX', 'BOLT EV', 'BOLT EUV', 'VOLT'], 'MAZDA': ['MAZDA6', '6', 'CX-5'],
         'SUBARU': ['LEGACY', 'OUTBACK', 'FORESTER'], 'VOLKSWAGEN': ['PASSAT', 'TIGUAN', 'ID.4'], 'GMC': ['TERRAIN'],
         'TESLA': ['MODEL 3', 'MODEL Y', 'MODEL S', 'MODEL X'], 'BMW': ['I3'], 'AUDI': ['E-TRON']}
src = sys.argv[1] if len(sys.argv) > 1 else 'FLAT_CMPL.txt'
with open(src, encoding='latin-1') as f, gzip.open('hk.tsv.gz', 'wt', encoding='latin-1') as h, gzip.open('peer.tsv.gz', 'wt', encoding='latin-1') as p:
    for line in f:
        c = line.split('\t', 6)
        if len(c) < 6: continue
        mk, md = c[3].strip().upper(), c[4].strip().upper()
        if mk in MAKES_TARGET: h.write(line)
        elif mk in PEERS and md in PEERS[mk]: p.write(line)
print('done')
