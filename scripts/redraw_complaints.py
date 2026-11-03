# NHTSA 원본(COMPLAINTS_RECEIVED_2010~2024) 재집계 → 월별/연간 차트 재작성
# 기준: 기아_확장/dpa/run_theta2.py CONFIG(대상 차종·연식, ENGINE 부품, 치명 키워드|화재|충돌), ODINO 중복제거, 접수일(LDATE)
import sys, os, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt, matplotlib.dates as mdates
from matplotlib import font_manager as fm
BASE=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','src'))
from ews_core import load_nhtsa, classify, in_group
import run_theta2 as R
_fams=[]
for f in fm.findSystemFonts():
    if 'NotoSansCJK-Regular' in f or 'malgun.ttf' in f.lower():
        fm.fontManager.addfont(f); _fams.append(fm.FontProperties(fname=f).get_name())
plt.rcParams['font.family']=sorted(set(_fams),key=lambda n:'Malgun' not in n)+['sans-serif']; plt.rcParams['axes.unicode_minus']=False; plt.rcParams['font.size']=15
C=R.CONFIG
src=sys.argv[1] if len(sys.argv)>1 else [os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data','nhtsa','hk.tsv.gz')]
df=classify(load_nhtsa(src if isinstance(src,list) else [src]),C['component_re'],C['critical_re'])
df['ENG']=df['COMPDESC'].fillna('').str.upper().str.contains('ENGINE').astype(int); df['CRIT']=df['CRIT'].astype(int)
g=df[in_group(df,C['target'])].groupby('ODINO').agg(T=('LD','min'),CRIT=('CRIT','max'),ENG=('ENG','max')).dropna(subset=['T'])
g['M']=g['T'].dt.to_period('M'); g['Y']=g['T'].dt.year
mon=g.groupby('M')[['ENG','CRIT']].sum().reindex(pd.period_range('2010-01','2019-12',freq='M'),fill_value=0)
yr=g.groupby('Y')[['ENG','CRIT']].sum().loc[2015:2020]
# 감사보고서 기준 판매보증충당부채전입액(연결 현금흐름표)·매출액
pv=pd.read_excel(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data','dart','분기별충당부채_감사보고서기준.xlsx'))
a=pv.groupby('연도').agg(prov=('분기별 설정액(백만단위)','sum'),rev=('매출액','sum')).loc[2015:2020]
a['rate']=a.prov*1e6/a.rev*100; a['prov_tr']=a.prov/1e6
out=pd.concat([yr,a[['prov_tr','rate']]],axis=1); out.columns=['엔진민원_전체','치명결함민원','전입액_조원','설정률_%']
out.drop(columns='엔진민원_전체').to_csv('연간_민원_설정률.csv',encoding='utf-8-sig')
NAVY='#1F3A5F'; GRAY='#B8BEC6'; ORG='#E8A33D'; RED='#C8102E'; PUR='#6B4C9A'
# ① 분기별 (EWS 분석 단위와 동일)
g['Q']=g['T'].dt.to_period('Q')
qs=g.groupby('Q')['CRIT'].sum().reindex(pd.period_range('2012Q1','2020Q4',freq='Q'),fill_value=0)
qs.rename('치명결함민원').to_csv('분기별_민원.csv',encoding='utf-8-sig')
fig,ax=plt.subplots(figsize=(16,9),dpi=300)
xi=range(len(qs)); ax.plot(xi,qs.values,color=NAVY,lw=3.2,marker='o',ms=6,label='치명 결함 민원 (분기)')
ev=[('2015Q3',RED,'15V-568 1차 리콜 (2015.09)',-0.12),('2017Q2',ORG,'17V-226 확대 리콜 (2017.04)',-0.12),('2017Q2',PUR,'NHTSA RQ17-004 조사 (2017.05)',0.12)]
for q,c,l,off in ev:
    ax.axvline(list(qs.index).index(pd.Period(q,'Q'))+off,color=c,ls='--',lw=2,label=l)
for q in ['2015Q4','2017Q2','2019Q1']:
    i=list(qs.index).index(pd.Period(q,'Q')); ax.annotate(f'{int(qs.iloc[i])}건',(i,qs.iloc[i]),xytext=(0,12),textcoords='offset points',ha='center',color=NAVY,fontsize=15,fontweight='bold')
ax.set_xticks([i for i,q in enumerate(qs.index) if q.quarter==1]); ax.set_xticklabels([str(q.year) for q in qs.index if q.quarter==1])
ax.set_xticks(list(xi),minor=True); ax.set_xlim(-0.5,len(qs)-0.5); ax.set_ylim(0,qs.max()*1.15)
ax.set_title(f'NHTSA 세타2 엔진 치명 결함 분기별 민원과 규제 조치 (2012Q1~2020Q4)',fontsize=22,fontweight='bold',loc='left')
ax.set_ylabel('치명 결함 민원 (건/분기)'); ax.grid(axis='y',alpha=.3); [ax.spines[s_].set_visible(False) for s_ in ('top','right')]
ax.legend(loc='upper left',frameon=False,fontsize=14)
fig.text(.01,.01,'자료: NHTSA FLAT_CMPL 접수일(LDATE) 기준 분기 집계, 민원번호(ODINO) 중복제거. 치명=엔진 부품 & 치명 키워드/화재/충돌. 대상: 세타2 GDI 탑재 Sonata 11-19·Santa Fe Sport 13-18·Santa Fe 19·Tucson 14/15/18/19',fontsize=11,color='#666')
fig.tight_layout(rect=(0,.03,1,1)); fig.savefig('①_분기별_민원_수정.png'); plt.close(fig)
print(qs.to_string())
# ② 연간
fig,ax=plt.subplots(figsize=(16,9),dpi=300)
yrs=out.index.astype(str)
b=ax.bar(yrs,out['전입액_조원'],color='#8C9DD1',width=.6,label='판매보증충당부채 전입액 (조원)')
for i,(v,r) in enumerate(zip(out['전입액_조원'],out['설정률_%'])):
    ax.text(i,v+.08,f'{v:.2f}조\n(설정률 {r:.2f}%)',ha='center',va='bottom',fontsize=14,color='#333')
ax.set_ylabel('전입액 (조원)'); ax.set_ylim(0,out['전입액_조원'].max()*1.35)
ax2=ax.twinx(); ax2.plot(yrs,out['치명결함민원'],color=ORG,lw=3,marker='o',ms=8,label='치명 결함 민원 (건)')
for i,v in enumerate(out['치명결함민원']): ax2.annotate(f'{int(v)}건',(i,v),xytext=(0,10),textcoords='offset points',ha='center',color='#B8741A',fontweight='bold',fontsize=16)
ax2.set_ylabel('치명 결함 민원 (건)'); ax2.set_ylim(0,out['치명결함민원'].max()*1.3)
for s in ('top',): ax.spines[s].set_visible(False); ax2.spines[s].set_visible(False)
ax.set_title('외부 위험 신호와 회계 반응 시점의 차이 — 민원은 2019년까지 증가, 설정률은 2020년 급등',fontsize=20,fontweight='bold',loc='left')
h1,l1=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels(); ax.legend(h1+h2,l1+l2,loc='upper left',frameon=False)
fig.text(.01,.01,'자료: NHTSA(접수일·ODINO 중복제거, 치명=엔진 부품 & 치명 키워드/화재/충돌), 현대차 연결 감사보고서 현금흐름표 판매보증충당부채전입액 ÷ 매출액',fontsize=11,color='#666')
fig.tight_layout(rect=(0,.03,1,1)); fig.savefig('②_연간_민원_설정률_수정.png'); plt.close(fig)
print(out.round(2).to_string())
