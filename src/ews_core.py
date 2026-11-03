# -*- coding: utf-8 -*-
"""
DPA-EWS : Disproportionality + CUSUM + Accounting-Response Early Warning System
-------------------------------------------------------------------------------
공개 결함신고 데이터(NHTSA 등)로 '제품 결함 위험의 구조적 상승'을 탐지하고,
같은 시점의 충당부채(판매보증·리콜) 설정률이 반응했는지를 점검하는 감사용 조기경보 모델.

설계 원칙 (모두 발표 방어 논리와 1:1 대응)
 1) Point-in-time : 분기 t 신호는 t분기 말까지 '접수(LDATE)'된 민원만 사용 → 사후정보(look-ahead) 차단
 2) 동일 잣대     : 대상군과 대조군(동급 경쟁 차종)에 '같은 분류기'를 적용 → NHTSA 전체 신고량 변화·홍보효과 통제
 3) 검증된 통계   : KEY1 PRR(약물감시 FDA/EMA 표준 불균형분석, Evans 기준) + KEY2 Poisson CUSUM(통계적 공정관리)
 4) 임계값 보정   : CUSUM 임계값 h는 '대조군 플라시보 오경보율 ≤ 5%'로 데이터에서 보정 (임의 설정 배제)
 5) 회계 연결     : KEY3는 금액을 '맞히지' 않음. 신호 지속 중 TTM 설정률 무반응을 '추정 재검토 트리거'로만 산출 (ISA 540)

배터리 등 타 산업 적용: CONFIG의 target / peer / component_re / critical_re 만 바꾸면 동일하게 작동.
"""
import numpy as np
import pandas as pd
from scipy import stats

# NHTSA FLAT_CMPL 필드(1~51) 이름
NHTSA_COLS = ['CMPLID', 'ODINO', 'MFR_NAME', 'MAKETXT', 'MODELTXT', 'YEARTXT', 'CRASH', 'FAILDATE', 'FIRE',
              'INJURED', 'DEATHS', 'COMPDESC', 'CITY', 'STATE', 'VIN', 'DATEA', 'LDATE', 'MILES', 'OCCURENCES',
              'CDESCR', 'CMPL_TYPE'] + [f'F{i}' for i in range(22, 52)]


def load_nhtsa(paths):
    """NHTSA 탭구분 원본(또는 .gz) → DataFrame. 행 단위=민원×부품이므로 이후 ODINO로 중복 제거."""
    frames = [pd.read_csv(p, sep='\t', header=None, names=NHTSA_COLS, dtype=str, quoting=3,
                          encoding='latin-1', on_bad_lines='skip') for p in paths]
    df = pd.concat(frames, ignore_index=True)
    df['MAKETXT'] = df['MAKETXT'].str.strip().str.upper()
    df['MODELTXT'] = df['MODELTXT'].str.strip().str.upper()
    df['YR'] = pd.to_numeric(df['YEARTXT'], errors='coerce')
    df['LD'] = pd.to_datetime(df['LDATE'], format='%Y%m%d', errors='coerce')   # 접수일 (point-in-time 기준)
    df['FD'] = pd.to_datetime(df['FAILDATE'], format='%Y%m%d', errors='coerce')  # 사고일 (사후분석용)
    return df


def in_group(df, spec):
    """spec = {MAKE: {MODEL: (연식from, 연식to) 또는 [연식 리스트]}}"""
    m = pd.Series(False, index=df.index)
    for make, models in spec.items():
        for model, yrs in models.items():
            yr_ok = df['YR'].between(*yrs) if isinstance(yrs, tuple) else df['YR'].isin(yrs)
            m |= (df['MAKETXT'] == make) & (df['MODELTXT'] == model) & yr_ok
    return m


def classify(df, component_re, critical_re):
    """치명 결함(critical) = 대상 부품 AND (치명 키워드 OR 화재 OR 충돌)."""
    comp = df['COMPDESC'].fillna('').str.upper().str.contains(component_re, regex=True)
    txt = df['CDESCR'].fillna('').str.upper()
    kw = txt.str.contains(critical_re, regex=True)
    out = df.copy()
    out['COMP_HIT'] = comp
    out['CRIT'] = comp & (kw | (df['FIRE'] == 'Y') | (df['CRASH'] == 'Y'))
    return out


def quarterly_counts(df, mask, time_col='LD'):
    """민원(ODINO) 단위로 집계: 전체 민원 n, 치명 결함 민원 a. 한 민원에 부품이 여러 개면 CRIT 하나라도 True면 치명."""
    g = df[mask].groupby('ODINO').agg(T=(time_col, 'min'), CRIT=('CRIT', 'max'), FIRE=('FIRE', lambda s: (s == 'Y').any()))
    g = g.dropna(subset=['T'])
    g['Q'] = g['T'].dt.to_period('Q')
    q = g.groupby('Q').agg(n=('CRIT', 'size'), a=('CRIT', 'sum'), fire=('FIRE', 'sum'))
    return q


# ---------------- KEY 1 : PRR (Proportional Reporting Ratio) ----------------
def _prr(a, n_t, c, n_p):
    b, dd = n_t - a, n_p - c
    with np.errstate(divide='ignore', invalid='ignore'):
        prr = (a / n_t) / (c / n_p)
        se = np.sqrt(1 / a - 1 / n_t + 1 / c - 1 / n_p)
        lo, hi = np.exp(np.log(prr) - 1.96 * se), np.exp(np.log(prr) + 1.96 * se)
        N = n_t + n_p
        chi = N * (np.abs(a * dd - b * c) - N / 2) ** 2 / (n_t * n_p * (a + c) * (b + dd))
    evans = (prr >= 2) & (chi >= 4) & (a >= 3) & (lo > 1)   # Evans et al.(2001) + CI 하한 > 1
    return prr, lo, hi, chi, evans


def prr_table(tq, pq, qrange=None):
    """tq: 대상군 분기표(n,a), pq: 대조군 분기표(n,a). 2x2 → PRR, 95% CI, Yates χ².
    KEY1   : 당분기 PRR이 Evans 기준 충족 (단기 불균형)
    KEY1_4Q: 최근 4분기 누적(TTM) PRR이 Evans 기준 충족 (지속 불균형, TTM 설정률과 기간 일치)"""
    d = pd.DataFrame({'a': tq['a'], 'n_t': tq['n'], 'c': pq['a'], 'n_p': pq['n']})
    if qrange is not None:
        d = d.reindex(pd.period_range(*qrange, freq='Q'))
    d = d.fillna(0)
    d['PRR'], d['PRR_lo'], d['PRR_hi'], d['CHI2'], d['KEY1'] = _prr(d['a'], d['n_t'], d['c'], d['n_p'])
    r = d[['a', 'n_t', 'c', 'n_p']].rolling(4, min_periods=4).sum()
    d['a_4Q'] = r['a']
    d['PRR_4Q'], d['PRR_4Q_lo'], _, d['CHI2_4Q'], d['KEY1_4Q'] = _prr(r['a'], r['n_t'], r['c'], r['n_p'])
    return d


# ---------------- KEY 2 : Poisson CUSUM (peer-adjusted expected) ----------------
def cusum(d, k=1.5, h=4.0, base_win=8, guard=1, min_base=4):
    """
    기대 건수 E_t = n_t × (대조군 치명비율 c_t/n_p_t) × PRR_base
      PRR_base = t-guard 이전 base_win개 분기 PRR 중앙값 (point-in-time, 자기 과거 대비 '추가 상승'만 포착)
    Lucas Poisson CUSUM: S_t = max(0, S_{t-1} + a_t ln k − (k−1) E_t),  S_t > h → 경보 후 0으로 리셋
    """
    d = d.copy()
    prr_hist = d['PRR'].replace([np.inf, -np.inf], np.nan)
    base = prr_hist.shift(guard).rolling(base_win, min_periods=min_base).median()
    d['PRR_base'] = base
    d['E'] = d['n_t'] * (d['c'] / d['n_p']) * base
    S, s_list, alarm = 0.0, [], []
    for a, E in zip(d['a'], d['E']):
        if np.isnan(E) or E <= 0:
            s_list.append(np.nan); alarm.append(False); S = 0.0; continue
        S = max(0.0, S + a * np.log(k) - (k - 1) * E)
        hit = S > h
        s_list.append(S); alarm.append(hit)
        if hit:
            S = 0.0
    d['CUSUM'] = s_list
    d['KEY2'] = alarm
    d['OE'] = d['a'] / d['E']           # 관측/기대 배수 (설명용)
    return d


# ---------------- KEY 3 : 회계 반응 (TTM 설정률) ----------------
def accounting_response(prov, delta_pp=0.25):
    """
    prov: index=Period[Q], columns=['provision','revenue'] (같은 단위)
    TTM 설정률 = 최근 4분기 설정액 합 ÷ 최근 4분기 매출 합  (분기 계절성·Q4 역산 노이즈 제거)
    반응(RESP) = TTM 설정률이 전분기 대비 +delta_pp(%p) 이상 상승
    """
    p = prov.copy()
    p['TTM_rate'] = p['provision'].rolling(4).sum() / p['revenue'].rolling(4).sum() * 100
    p['dTTM_pp'] = p['TTM_rate'].diff()
    p['RESP'] = p['dTTM_pp'] >= delta_pp
    return p


def combine(sig, acct, resp_window=4):
    """
    ONSET   = KEY2(CUSUM 경보)                                   → '새 위험 발생'
    PERSIST = KEY1_4Q(최근 4분기 누적 PRR 유의)                    → '위험 미해소' (K-IFRS 1037 문단59 매기 재검토 대상)
    RISK    = ONSET or PERSIST
    회계 반응 여부 = 최근 resp_window분기(당기 포함) 안에 RESP(TTM 설정률 유의 상승)가 있었는가
    등급: RED   = RISK & 최근 1년 회계 반응 없음  → 추정 재검토 트리거 (독립추정·경영진 질의·KAM 검토)
          AMBER = RISK & 최근 1년 내 반응은 있었음 → 반응 규모 적정성 확인
          GREEN = RISK 없음
    """
    x = sig.join(acct[['TTM_rate', 'dTTM_pp', 'RESP']], how='left')
    k1 = x['KEY1_4Q'].fillna(False).astype(bool)
    run1 = k1.astype(int).groupby((~k1).cumsum()).cumsum()
    x['PERSIST_RUN'] = run1                       # TTM PRR 유의 연속 분기 수
    x['ONSET'] = x['KEY2'].fillna(False).astype(bool)
    x['PERSIST'] = k1
    x['RISK'] = x['ONSET'] | x['PERSIST']
    resp = x['RESP'].astype(float)
    x['RESP_1Y'] = resp.rolling(resp_window, min_periods=1).max()
    has_acct = x['TTM_rate'].notna()
    x['GRADE'] = np.select([x['RISK'] & has_acct & (x['RESP_1Y'] != 1), x['RISK'] & has_acct, x['RISK']],
                           ['RED', 'AMBER', 'RISK(회계자료 없음)'], 'GREEN')
    return x


def calibrate_h(placebo_tables, k=1.5, grid=np.arange(1.0, 10.01, 0.25), target_far=0.05, **kw):
    """대조군(결함 이슈 없는 동급 차종)을 대상군으로 가정한 플라시보 → 분기당 오경보율 ≤ target_far 인 최소 h."""
    res = []
    for h in grid:
        alarms, total = 0, 0
        for d in placebo_tables:
            c = cusum(d, k=k, h=h, **kw)
            valid = c['E'].notna()
            alarms += c.loc[valid, 'KEY2'].sum(); total += valid.sum()
        res.append((h, alarms / max(total, 1)))
    res = pd.DataFrame(res, columns=['h', 'FAR'])
    ok = res[res['FAR'] <= target_far]
    return (ok['h'].min() if len(ok) else grid.max()), res
