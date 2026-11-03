import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from ews_core import *
from run_theta2 import CONFIG, build
P=pd.read_pickle('panel.pkl'); df=P['df']
peer_mask=in_group(df,CONFIG['peer'])
# --- placebo tables: 각 대조군 브랜드를 '대상'으로, 나머지 대조군을 '대조'로
plac={}
for mk,models in CONFIG['peer'].items():
    t=in_group(df,{mk:models}); rest=peer_mask&~t
    plac[mk]=build(quarterly_counts(df,t),quarterly_counts(df,rest))
h_star,far=calibrate_h(list(plac.values()),k=1.5)
print('calibrated h =',h_star); print(far[far.h.isin([2,3,4,5,6,7,8])].to_string(index=False))
pd.to_pickle(dict(plac=plac,h=h_star,far=far),'calib.pkl')
