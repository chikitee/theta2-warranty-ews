# -*- coding: utf-8 -*-
"""현대차 세타2 EWS 3단 그래프 재현 (발표 S15·S16과 같은 규칙)
입력 : panel.pkl(run_theta2.py), calib.pkl(calibrate_h.py), data/dart/분기별충당부채_감사보고서기준.xlsx(연결 현금흐름표 전입액·매출)
출력 : docs/images/hyundai_theta2_ews.png
사용 : cd src && python run_theta2.py && python calibrate_h.py && python make_hyundai_chart.py"""
import os, glob, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, matplotlib.font_manager as fm
from ews_core import cusum, accounting_response, combine
from run_theta2 import build

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
Q0, Q1, BASE = '2013Q1', '2022Q4', ('2013Q1', '2015Q1')   # 평시 변동폭 = 위험 신호 이전 구간
NAVY, RED, GREEN, GREY, SLATE, PINK = '#14213D', '#D62828', '#6AA121', '#C9D1DB', '#5C677D', '#FBE3E3'
EVENTS = [('2015-09-10', '1차 리콜'), ('2017-03-31', '확대 리콜·\nNHTSA 조사'), ('2020-11-23', 'NHTSA\n동의명령')]

def set_font():
    for pat in ['C:/Windows/Fonts/malgun*.ttf', '/usr/share/fonts/truetype/nanum/NanumGothic*.ttf',
                '/System/Library/Fonts/AppleSDGothicNeo.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
        fs = sorted(glob.glob(pat))
        if fs:
            for f in fs: fm.fontManager.addfont(f)
            plt.rcParams['font.family'] = fm.FontProperties(fname=fs[0]).get_name(); break
    plt.rcParams['axes.unicode_minus'] = False

def load_prov():
    x = pd.read_excel(os.path.join(ROOT, 'data', 'dart', '분기별충당부채_감사보고서기준.xlsx'))
    idx = pd.PeriodIndex([f'{a}Q{b}' for a, b in zip(x['연도'], x['분기'])], freq='Q')
    return pd.DataFrame({'provision': x['분기별 설정액(백만단위)'].values * 1e6, 'revenue': x['매출액'].values}, index=idx)

def main():
    set_font()
    P, H = pd.read_pickle(os.path.join(HERE, 'panel.pkl')), pd.read_pickle(os.path.join(HERE, 'calib.pkl'))['h']
    prov = load_prov(); d = accounting_response(prov).loc[BASE[0]:BASE[1], 'dTTM_pp'].dropna()
    thr = 1.645 * 1.4826 * np.median(np.abs(d - d.median()))
    r = combine(cusum(build(P['Tq'], P['Pq']), k=1.5, h=H), accounting_response(prov, delta_pp=thr)).loc[Q0:Q1]
    x = np.array([q.year + (q.quarter - 1) / 4 for q in r.index]); red = (r['GRADE'] == 'RED').values
    s0 = r.index[r['KEY1_4Q'].fillna(False).astype(bool)][0]; resp = r.index[(r['RESP'] == True) & (r.index >= s0)]
    fig, ax = plt.subplots(3, 1, figsize=(19.2, 10.8), sharex=True, gridspec_kw={'height_ratios': [2.3, 1.4, 2.6], 'hspace': .45})
    for a in ax:
        for xi, on in zip(x, red):
            if on: a.axvspan(xi - .125, xi + .125, color=PINK, lw=0, zorder=0)
        for dt, lab in EVENTS:
            t = pd.Timestamp(dt); a.axvline(t.year + (t.dayofyear - 1) / 365.25, color=SLATE, lw=1, ls=':', zorder=1)
        for s in ('top', 'right'): a.spines[s].set_visible(False)
        a.grid(axis='y', color='#EEF1F5'); a.tick_params(labelsize=12)
    for dt, lab in EVENTS:
        t = pd.Timestamp(dt); ax[0].text(t.year + (t.dayofyear - 1) / 365.25 + .04, 1.0, lab, transform=ax[0].get_xaxis_transform(), va='top', fontsize=11, color=SLATE)
    # ① 위험 신호
    a = ax[0]; hi = r['PRR_4Q'] ** 2 / r['PRR_4Q_lo']
    a.fill_between(x, r['PRR_4Q_lo'], hi, color=NAVY, alpha=.1, lw=0); a.plot(x, r['PRR_4Q'], color=NAVY, lw=2.6)
    a.axhline(2, color=RED, ls='--', lw=1.4); a.text(x[0], 2.12, '위험 기준선: 경쟁차의 2배', color=RED, fontsize=12, fontweight='bold')
    a.annotate(f'{s0.year}년 {s0.quarter}분기 기준선 돌파 ({r.loc[s0, "PRR_4Q"]:.1f}배)', xy=(x[r.index.get_loc(s0)], r.loc[s0, 'PRR_4Q']),
               xytext=(x[0] + .4, 3.6), fontsize=12, fontweight='bold', arrowprops=dict(arrowstyle='-|>', color=NAVY))
    a.set_ylim(0, 4.6); a.set_title('① 위험 신호: 세타2 차량 민원 중 엔진 치명결함 비율이 동급 경쟁차 22종보다 몇 배 높은가', loc='left', fontsize=15, fontweight='bold')
    # ② 급증 감지
    a = ax[1]; cs = r['CUSUM'].fillna(0).values; al = r['KEY2'].fillna(False).values.astype(bool)
    a.bar(x, cs, width=.16, color=np.where(al, RED, GREY)); a.axhline(H, color=RED, ls='--', lw=1.3)
    a.text(x[0], H * 1.12, f'경보 기준선 h = {H:.2f}', color=RED, ha='left', fontsize=12); a.set_yticks([])
    a.set_title('② 급증 감지: 예상보다 민원이 갑자기 늘었는가 (빨간 막대 = 경보)', loc='left', fontsize=15, fontweight='bold')
    # ③ 회계 반응
    a = ax[2]; a.plot(x, r['TTM_rate'], color=NAVY, lw=2.4, marker='o', ms=5)
    ix = [r.index.get_loc(q) for q in resp]; a.scatter(x[ix], r['TTM_rate'].values[ix], s=130, color=GREEN, zorder=4, label=f'의미 있는 상승 (+{thr:.2f}%p 이상)')
    a.fill_between([], [], color=PINK, label='경고 구간 (위험 신호 + 1년간 반응 없음)'); a.legend(loc='upper left', frameon=False, fontsize=12)
    first = resp[0]; lag = (first - s0).n; nred = int(red[(r.index >= s0) & (r.index < first)].sum())
    a.annotate(f'{first.year}.{first.quarter}Q 첫 유의 상승\n(신호 후 {lag}분기)', xy=(x[ix[0]], r.loc[first, 'TTM_rate']), xytext=(x[ix[0]] - .3, 4.2),
               fontsize=12, color=GREEN, fontweight='bold', ha='center', arrowprops=dict(arrowstyle='-|>', color=GREEN))
    a.text(2016.6, 3.3, f'{nred}개 분기 연속 경고\n위험 신호는 계속, 설정률은 평시 변동 범위 내', color=RED, fontsize=13, fontweight='bold', ha='center')
    a.set_ylim(0, 6.2); a.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:.0f}%'))
    a.set_title('③ 회계 반응: 판매보증충당부채 설정률 = 최근 4분기 전입액 ÷ 매출', loc='left', fontsize=15, fontweight='bold')
    a.set_xticks(range(2013, 2023)); a.set_xlim(x[0] - .3, x[-1] + .3)
    fig.suptitle('현대차 세타2 엔진: 위험 신호가 이어지는 동안 설정률은 평시 범위에 머물렀다', x=.05, ha='left', fontsize=21, fontweight='bold')
    fig.text(.05, .015, '자료: NHTSA 민원(접수일 기준, 동급 22개 차종 대비), DART 현대자동차 연결 현금흐름표 판매보증충당부채전입액·매출. 평시 변동폭 = 신호 이전(2013~2015Q1) 분기 변화의 강건 표준편차 × 1.645.',
             fontsize=10.5, color=SLATE)
    fig.subplots_adjust(left=.05, right=.98, top=.9, bottom=.07)
    out = os.path.join(ROOT, 'docs', 'images', 'hyundai_theta2_ews.png'); fig.savefig(out, dpi=110, facecolor='white')
    print('saved', out, '| 임계', round(thr, 3), '| 신호', s0, '| 첫 반응', first, f'({lag}분기)', '| 경고 분기', nred)

if __name__ == '__main__':
    main()
