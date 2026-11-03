# -*- coding: utf-8 -*-
"""범용성 검증: 같은 DPA-EWS를 (1) 현대 세타2 (2) 기아 세타2 (3) LG화학 EV 배터리(볼트EV·코나EV) 에 적용
회계 반응 = 연결 주석 충당부채 변동표 '판매보증충당부채 전입(설정)액' (K-IFRS 1037 문단 84 공시, 기말잔액과 대사 가능) - 3사 동일
임계 = 1.645 × 강건σ(1.4826×MAD) : 분기 TTM 설정률 변화 / 전년 대비 변화 두 정의"""
import os, re, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from ews_core import *
from run_theta2 import CONFIG, build, D
from config_battery_template import BATTERY_CONFIG as B
HERE = os.path.dirname(os.path.abspath(__file__)); UP = os.path.join(HERE, '..', 'data', 'dart'); OUT = os.path.join(HERE, '..', 'results'); Z = 1.645
P = pd.read_pickle('panel.pkl'); H = pd.read_pickle('calib.pkl')['h']; df = P['df']

def prov_xlsx(path, sheet, s_col, r_col, r_scale):
    x = pd.read_excel(path, sheet_name=sheet).dropna(subset=['분기'])
    idx = pd.PeriodIndex([f"{int(a)}Q{int(b)}" for a, b in zip(x['연도'], x['분기'])], freq='Q')
    return pd.DataFrame({'provision': x[s_col].values * 1e6, 'revenue': x[r_col].values * r_scale}, index=idx)

def num(s):
    s = s.replace(' ', '').replace(',', ''); neg = s.startswith('(') or s.startswith('-'); s = re.sub(r'[^\d]', '', s)
    return (-1 if neg else 1) * int(s) if s else 0

def lgchem_prov():
    b = json.load(open(os.path.join(UP, 'opendart', 'lgchem_prov_all.json'), encoding='utf-8'))
    cum, rev = {}, {}
    for q, v in b.items():
        t = [t for t in v['tables'] if '연결' in t['ctx']][0]
        hdr = [h.strip() for h in t['rows'][1].split('|')]
        ci = next(i for i, h in enumerate(hdr) if '판매보증' in h)
        row = next(r for r in t['rows'] if re.match(r'^(충당금\s*)?(전입|설정|증가|추가)', r))
        cum[q] = num(row.split('|')[ci + 1])
        if v['rev']['thstrm']: rev[q] = num(v['rev']['thstrm']) / 1e6
    rows = []
    for q in sorted(cum):
        p = pd.Period(q, 'Q'); prev = str(p - 1)
        qs = cum[q] - (cum[prev] if p.quarter > 1 and prev in cum else 0)
        r = rev.get(q)
        if r is not None and p.quarter == 4:
            r = r - sum(rev.get(f'{p.year}Q{k}', np.nan) for k in (1, 2, 3))
        rows.append(dict(Q=p, provision=qs * 1e6, revenue=(r * 1e6 if r is not None else np.nan), cum=cum[q]))
    d = pd.DataFrame(rows).set_index('Q')
    d[['cum', 'provision', 'revenue']].assign(provision=lambda x: x.provision / 1e6, revenue=lambda x: x.revenue / 1e6).to_csv(
        os.path.join(UP, 'LG화학_분기별_판매보증전입_주석.csv'), encoding='utf-8-sig')
    return d[['provision', 'revenue']].dropna()

PROV = {'현대': prov_xlsx(os.path.join(UP, '현대_분기별충당부채_DART대조.xlsx'), '현대_분기_DART', '분기별 설정액(백만단위)', '매출액', 1),
        '기아': prov_xlsx(os.path.join(UP, '기아_분기별충당부채_DART.xlsx'), '기아_분기', '분기별 설정액(백만단위)', '매출액(백만원)', 1e6),
        'LG화학': lgchem_prov()}
kia_scope = {'KIA': {'OPTIMA': (2011, 2014), 'SORENTO': (2012, 2014), 'SPORTAGE': (2011, 2013)}}
raw = load_nhtsa([D + 'hk.tsv.gz', D + 'peer.tsv.gz']); raw = raw[in_group(raw, B['target']) | in_group(raw, B['peer'])]
bdf = classify(raw, B['component_re'], B['critical_re'])
SIG = {'현대': cusum(build(P['Tq'], P['Pq']), k=1.5, h=H),
       '기아': cusum(build(quarterly_counts(df, in_group(df, kia_scope)), P['Pq']), k=1.5, h=H),
       'LG화학': cusum(prr_table(quarterly_counts(bdf, in_group(bdf, B['target'])), quarterly_counts(bdf, in_group(bdf, B['peer'])),
                                qrange=('2016Q1', '2023Q3')), k=1.5, h=H)}
WIN = {'현대': ('2013Q1', '2022Q4'), '기아': ('2013Q1', '2022Q4'), 'LG화학': ('2016Q4', '2023Q3')}

res, info = {}, {}
for who in SIG:
    q0, q1 = WIN[who]
    a0 = accounting_response(PROV[who]); d = a0.loc[q0:q1, 'dTTM_pp'].dropna()
    s = 1.4826 * np.median(np.abs(d - d.median()))
    a = accounting_response(PROV[who], delta_pp=Z * s)
    y = (a.TTM_rate - a.TTM_rate.shift(4)); yy = y.loc[q0:q1].dropna(); sy = 1.4826 * np.median(np.abs(yy - yy.median()))
    a['RESP_Y'] = y >= Z * sy
    r = combine(SIG[who], a).loc[q0:q1]; r['RESP_Y'] = a['RESP_Y'].reindex(r.index); res[who] = r
    k1 = r.KEY1_4Q.fillna(False).astype(bool); s0 = k1[k1].index[0]
    rq = next((q for q in r.index[r.RESP == True] if q >= s0), None); ry = next((q for q in r.index[r.RESP_Y == True] if q >= s0), None)
    info[who] = dict(sig0=s0, prr=r.loc[s0, 'PRR_4Q'], lo=r.loc[s0, 'PRR_4Q_lo'], cus=[q for q in r.index[r.KEY2] if q >= s0 - 4],
                     rq=rq, ry=ry, thr_q=Z * s, thr_y=Z * sy,
                     red=[str(q) for q in r.index[r.GRADE == 'RED']], amber=[str(q) for q in r.index[r.GRADE == 'AMBER']])
    print(who, {k: (str(v) if not isinstance(v, list) else v) for k, v in info[who].items()})
pd.set_option('display.width', 250)
print(res['LG화학'].loc['2019Q1':'2022Q4', ['a', 'n_t', 'PRR_4Q', 'PRR_4Q_lo', 'KEY1_4Q', 'CUSUM', 'KEY2', 'TTM_rate', 'dTTM_pp', 'RESP', 'RESP_Y', 'GRADE']].round(2).to_string())
pd.to_pickle(dict(res=res, info=info), 'general_result.pkl')
with pd.ExcelWriter(os.path.join(OUT, '범용성_3사_DPA_결과.xlsx')) as w:
    pd.DataFrame([{**{'회사': k}, **{a: (str(b) if not isinstance(b, (float, int)) else round(b, 3)) for a, b in v.items()}} for k, v in info.items()]).to_excel(w, sheet_name='요약', index=False)
    for k, r in res.items(): r.reset_index(names='Quarter').astype({'Quarter': str}).round(4).to_excel(w, sheet_name=k, index=False)
