# -*- coding: utf-8 -*-
"""세타2(현대차) 적용 스크립트 — ews_core 알고리즘 + 설정만 교체하면 배터리 등에 재사용"""
import numpy as np, pandas as pd
from ews_core import *

import os
D = os.environ.get('EWS_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'nhtsa', ''))   # hk.tsv.gz, peer.tsv.gz 위치
CONFIG = dict(
    # 대상군: 세타2 GDI 탑재 차종·연식 (미국 집단소송 합의·KSDS 캠페인 대상 기준)
    target={'HYUNDAI': {'SONATA': (2011, 2019), 'SANTA FE SPORT': (2013, 2018), 'SANTA FE': [2019],
                        'TUCSON': [2014, 2015, 2018, 2019]}},
    # 대조군: 동일 연식(2011~2019) 동급 중형 세단·SUV 경쟁 차종
    peer={'TOYOTA': {'CAMRY': (2011, 2019), 'RAV4': (2011, 2019), 'HIGHLANDER': (2011, 2019)},
          'HONDA': {'ACCORD': (2011, 2019), 'CR-V': (2011, 2019), 'PILOT': (2011, 2019)},
          'NISSAN': {'ALTIMA': (2011, 2019), 'ROGUE': (2011, 2019), 'MURANO': (2011, 2019)},
          'FORD': {'FUSION': (2011, 2019), 'ESCAPE': (2011, 2019), 'EDGE': (2011, 2019)},
          'CHEVROLET': {'MALIBU': (2011, 2019), 'EQUINOX': (2011, 2019)},
          'MAZDA': {'MAZDA6': (2011, 2019), '6': (2011, 2019), 'CX-5': (2011, 2019)},
          'SUBARU': {'LEGACY': (2011, 2019), 'OUTBACK': (2011, 2019), 'FORESTER': (2011, 2019)},
          'VOLKSWAGEN': {'PASSAT': (2011, 2019), 'TIGUAN': (2011, 2019)},
          'GMC': {'TERRAIN': (2011, 2019)}},
    kia={'KIA': {'OPTIMA': (2011, 2019), 'SORENTO': (2012, 2019), 'SPORTAGE': (2011, 2019)}},
    component_re=r'ENGINE',   # 'POWER TRAIN'(변속기)은 제외: 닛산 CVT 등 대조군 오염 방지
    critical_re=(r'KNOCK|SEIZ|BEARING|CONNECTING ROD|THR(E|O)W(N|ING)? A ROD|ENGINE (FAIL|DIED|BLEW|BLOWN|EXPLOD|LOCKED)'
                 r'|BLEW (THE |MY |UP )?(THE )?ENGINE|HOLE IN THE (ENGINE )?BLOCK|METAL (SHAVING|DEBRIS|FRAGMENT|PIECES)'
                 r'|STALL|SHUT (OFF|DOWN)|LOST (ALL |MOTIVE )?POWER|LOSS OF (MOTIVE |ALL )?POWER|NO POWER'
                 r'|CAUGHT FIRE|ON FIRE|FIRE|SMOKE|FLAME|EXCESSIVE (AMOUNT OF )?(ENGINE )?OIL|OIL CONSUMPTION|CONSUM(ING|ES|ED) OIL'
                 r'|ENGINE (WAS |HAD TO BE |NEEDS TO BE |NEEDED TO BE )?REPLACE|NEW ENGINE|REPLACE(D|MENT OF)? (THE )?ENGINE|TICKING|TAPPING'),
    qmin='2010Q1', qmax='2022Q4',
)

def build(prr_target, prr_peer):
    return prr_table(prr_target, prr_peer, qrange=(CONFIG['qmin'], CONFIG['qmax']))

if __name__ == '__main__':
    raw = load_nhtsa([D + 'hk.tsv.gz', D + 'peer.tsv.gz'])
    df = classify(raw, CONFIG['component_re'], CONFIG['critical_re'])
    tgt, peer, kia = (in_group(df, CONFIG[k]) for k in ('target', 'peer', 'kia'))
    Tq, Pq, Kq = quarterly_counts(df, tgt), quarterly_counts(df, peer), quarterly_counts(df, kia)
    pd.to_pickle(dict(df=df[tgt | peer | kia], Tq=Tq, Pq=Pq, Kq=Kq), 'panel.pkl')
    print(pd.concat({'T': Tq, 'P': Pq, 'K': Kq}, axis=1).loc['2010Q1':'2021Q4'].to_string())
