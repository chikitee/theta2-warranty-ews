# -*- coding: utf-8 -*-
"""OpenDART: 회사별 정기보고서 원문 다운로드 + 연결 '판매보증충당부채' 변동표 원문 표 덤프 + 연결 매출액
사용: OPENDART_KEY=... python3 opendart_fetch.py <corp_code> <bgn YYYYMMDD> <end YYYYMMDD> <tag>"""
import os, sys, re, json, time, zipfile, html, urllib.request
KEY = os.environ['OPENDART_KEY']; corp, bgn, end, tag = sys.argv[1:5]
def get(url):
    with urllib.request.urlopen(url, timeout=120) as u: return u.read()
lst = []
for ty in ['A001', 'A002', 'A003']:
    j = json.loads(get(f'https://opendart.fss.or.kr/api/list.json?crtfc_key={KEY}&corp_code={corp}&bgn_de={bgn}&end_de={end}&pblntf_detail_ty={ty}&last_reprt_at=Y&page_count=100'))
    lst += j.get('list', [])
def period(nm):
    m = re.search(r'\((\d{4})\.(\d{2})\)', nm); y, mo = int(m.group(1)), int(m.group(2)); return f'{y}Q{mo // 3}'
R = {}
for it in lst:
    q = period(it['report_nm']); R[q] = it['rcept_no']  # last_reprt_at=Y → 최종본
os.makedirs(f'zip_{tag}', exist_ok=True)
CODE = {1: '11013', 2: '11012', 3: '11014', 4: '11011'}
def clean(s): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()
out = {}
for q in sorted(R):
    r = R[q]; p = f'zip_{tag}/{r}.zip'
    if not os.path.exists(p): open(p, 'wb').write(get(f'https://opendart.fss.or.kr/api/document.xml?crtfc_key={KEY}&rcept_no={r}')); time.sleep(0.8)
    z = zipfile.ZipFile(p); tabs = []
    for fn in z.namelist():
        b = z.read(fn)
        try: x = b.decode('utf-8')
        except UnicodeDecodeError: x = b.decode('cp949', 'ignore')
        ctx = ''
        for m in re.finditer(r'<TITLE[^>]*>(.*?)</TITLE>|<TABLE[^>]*>(.*?)</TABLE>', x, re.S | re.I):
            if m.group(1) is not None:
                t = clean(m.group(1))
                if '재무제표' in t or '보고서' in t: ctx = t
                continue
            tb = m.group(2); txt = clean(tb)
            if '판매보증' in txt and re.search(r'기초|기말', txt) and re.search(r'전입|설정|증가|추가', txt):
                rows = [' | '.join(clean(c) for c in re.findall(r'<T[DEUH][^>]*>(.*?)</T[DEUH]>', tr, re.S | re.I))
                        for tr in re.findall(r'<TR[^>]*>(.*?)</TR>', tb, re.S | re.I)]
                tabs.append(dict(ctx=ctx[:30], rows=rows[:14]))
    y, qq = int(q[:4]), int(q[-1])
    try:
        j = json.loads(get(f'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json?crtfc_key={KEY}&corp_code={corp}&bsns_year={y}&reprt_code={CODE[qq]}'))
        rev = [a for a in j.get('list', []) if a['fs_div'] == 'CFS' and a['account_nm'] in ('매출액', '수익(매출액)', '영업수익')]
        rv = rev[0] if rev else {}
    except Exception as e: rv = {'err': str(e)}
    out[q] = dict(rcp=r, tables=tabs, rev=dict(thstrm=rv.get('thstrm_amount'), add=rv.get('thstrm_add_amount')))
    print(q, r, '| tables', len(tabs), '| rev', rv.get('thstrm_amount'), rv.get('thstrm_add_amount'))
json.dump(out, open(f'{tag}_prov.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
