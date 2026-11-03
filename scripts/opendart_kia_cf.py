# -*- coding: utf-8 -*-
"""OpenDART 원문(document.xml)에서 기아 연결 '영업활동 조정' 판매보증 전입액(현대와 동일 기준) 추출
사용: OPENDART_KEY=... python3 opendart_kia_cf.py   (키는 환경변수로만 전달)"""
import os, re, io, time, zipfile, json, urllib.request, html
KEY = os.environ['OPENDART_KEY']
RCP = {  # 기아(00106641) 정기보고서 접수번호 (사업보고서는 최신 정정본)
 '2012Q1':'20120530000979','2012Q2':'20120829000594','2012Q3':'20121129001060','2012Q4':'20130401003001',
 '2013Q1':'20130515001208','2013Q2':'20130814001393','2013Q3':'20131114001230','2013Q4':'20140331002985',
 '2014Q1':'20140515001462','2014Q2':'20140814001462','2014Q3':'20141114001373','2014Q4':'20211210000409',
 '2015Q1':'20150515002422','2015Q2':'20150817001619','2015Q3':'20151116001596','2015Q4':'20211210000418',
 '2016Q1':'20160516003622','2016Q2':'20160816001824','2016Q3':'20161114002424','2016Q4':'20211210000438',
 '2017Q1':'20170515004513','2017Q2':'20170814002201','2017Q3':'20171114002725','2017Q4':'20211210000450',
 '2018Q1':'20180515002353','2018Q2':'20180814002685','2018Q3':'20181114002573','2018Q4':'20211210000468',
 '2019Q1':'20190515002374','2019Q2':'20190814002373','2019Q3':'20191114002317','2019Q4':'20211210000477',
 '2020Q1':'20200515002459','2020Q2':'20200814002449','2020Q3':'20201116001829','2020Q4':'20211210000500',
 '2021Q1':'20210517001976','2021Q2':'20210817002003','2021Q3':'20211115002339','2021Q4':'20220321000650',
 '2022Q1':'20220516002405','2022Q2':'20220816002156','2022Q3':'20221114002323','2022Q4':'20230309000734'}
os.makedirs('zip', exist_ok=True)
TOK = re.compile(r'<TITLE[^>]*>(.*?)</TITLE>|<TABLE[^>]*>(.*?)</TABLE>', re.S | re.I)
ROW = re.compile(r'<TR[^>]*>(.*?)</TR>', re.S | re.I)
CELL = re.compile(r'<T[DEUH][^>]*>(.*?)</T[DEUH]>', re.S | re.I)
def clean(s): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()
def num(s):
    s = s.replace(',', '').strip(); neg = s.startswith('(') or s.startswith('-')
    s = re.sub(r'[^\d.]', '', s)
    return (-1 if neg else 1) * float(s) if s else None
out = {}
for q, r in RCP.items():
    p = f'zip/{r}.zip'
    if not os.path.exists(p):
        with urllib.request.urlopen(f'https://opendart.fss.or.kr/api/document.xml?crtfc_key={KEY}&rcept_no={r}', timeout=90) as u:
            open(p, 'wb').write(u.read())
        time.sleep(1.0)
    z = zipfile.ZipFile(p); hits = []
    for fn in z.namelist():
        b = z.read(fn)
        try: x = b.decode('utf-8')
        except UnicodeDecodeError: x = b.decode('cp949', 'ignore')
        title, ctx = '', ''
        for m in TOK.finditer(x):
            if m.group(1) is not None:
                t = clean(m.group(1)); title = t
                if '재무제표' in t or '검토보고서' in t or '감사보고서' in t: ctx = t
                continue
            tb = m.group(2); txt = clean(tb)
            if '판매보증' not in txt: continue
            is_cf = ('감가상각' in txt) and ('법인세' in txt) and ('원재료' not in txt)
            for row in ROW.findall(tb):
                c = [clean(v) for v in CELL.findall(row)]
                if c and re.match(r'^판매보증(비|충당부채\s*전입|충당금\s*전입|비용)', c[0]) and '지급' not in c[0]:
                    vals = [num(v) for v in c[1:] if num(v) is not None]
                    hits.append(dict(file=fn, ctx=ctx[:30], title=title[:30], cf=is_cf, label=c[0], vals=vals[:4]))
    out[q] = hits
    cf = [h for h in hits if h['cf']]
    print(q, r, '| CF:', [(h['ctx'][:14], h['label'], h['vals'][:2]) for h in cf][:4])
json.dump(out, open('kia_cf_hits.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
