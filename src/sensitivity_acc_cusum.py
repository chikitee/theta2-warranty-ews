# -*- coding: utf-8 -*-
"""DPA-EWS v3 (주석 기준 3사) - 회계반응 판정을 '사전에 정한 표준 규칙'으로 보강, 결과와 무관하게 3사 동일 적용
 R1 분기: ΔTTM ≥ 1.645σ                      (v2와 동일)
 R2 전년: TTM_t − TTM_{t-4} ≥ 1.645σ_YoY      (v2 보조)
 R3 누적(주 규칙): 회계 CUSUM  S_t = max(0, S_{t-1} + ΔTTM_t/σ − k), S_t > h  (Page CUSUM 표준값 k=0.5, h=4)
    → 신호측(Poisson CUSUM)과 대칭: '한 번에 크게'뿐 아니라 '여러 분기에 걸친 점진 증액'도 반응으로 인정 (보수적 = 회사에 유리)
 σ = 1.4826×MAD(ΔTTM, 분석구간). 민감도: k∈{0.25,0.5,0.75} × h∈{3,4,5}"""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
G = pd.read_pickle('general_result.pkl'); Z = 1.645
def acc_cusum(d, sig, k, h, start):
    S, out = 0.0, {}
    for q, v in d.items():
        if q < start or np.isnan(v): S = 0.0; out[q] = 0.0; continue
        S = max(0.0, S + v / sig - k); out[q] = S
    s = pd.Series(out); hit = s[s > h]
    return s, (hit.index[0] if len(hit) else None)
rows, keep = [], {}
for who, r in G['res'].items():
    s0 = G['info'][who]['sig0']; d = r['dTTM_pp']; dd = d.dropna()
    sig = 1.4826 * np.median(np.abs(dd - dd.median()))
    lag = lambda q: (q - s0).n if q is not None else None
    s_main, q_main = acc_cusum(d, sig, 0.5, 4.0, s0); keep[who] = dict(S=s_main, sig=sig)
    grid = {f'k{k}_h{h}': lag(acc_cusum(d, sig, k, h, s0)[1]) for k in (0.25, 0.5, 0.75) for h in (3, 4, 5)}
    rq, ry = G['info'][who]['rq'], G['info'][who]['ry']
    rows.append(dict(회사=who, 신호=str(s0), σ=round(sig, 3), R1_분기=f'{rq}({lag(rq)})', R2_전년=f'{ry}({lag(ry)})',
                     R3_누적CUSUM=f'{q_main}({lag(q_main)})', R3_민감도_범위=f'{min(v for v in grid.values() if v is not None)}~{max(v for v in grid.values() if v is not None)}', **grid))
S = pd.DataFrame(rows); pd.set_option('display.width', 250); print(S.to_string(index=False))
for who in keep: print(who, keep[who]['S'].loc[G['info'][who]['sig0']:].round(2).head(16).to_dict())
pd.to_pickle(dict(S=S, keep=keep), 'dpa_v3.pkl')
