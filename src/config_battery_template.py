# -*- coding: utf-8 -*-
"""배터리(예: LG에너지솔루션 셀 탑재 EV 화재) 적용 템플릿 — ews_core 알고리즘은 그대로, 설정만 교체"""
BATTERY_CONFIG = dict(
    # 대상군: 문제 셀 탑재 차종 (예시)
    target={'CHEVROLET': {'BOLT EV': (2017, 2022), 'BOLT EUV': (2022, 2022)},
            'HYUNDAI': {'KONA ELECTRIC': (2019, 2021)}},
    # 대조군: 동시대 타 배터리 공급사 EV
    peer={'NISSAN': {'LEAF': (2017, 2022)},
          'TESLA': {'MODEL 3': (2017, 2022), 'MODEL Y': (2020, 2022), 'MODEL S': (2017, 2022), 'MODEL X': (2017, 2022)},
          'BMW': {'I3': (2017, 2021)}, 'VOLKSWAGEN': {'ID.4': (2021, 2022)}, 'AUDI': {'E-TRON': (2019, 2022)}},
    component_re=r'ELECTRICAL SYSTEM|ELECTRIC PROPULSION|HYBRID PROPULSION|BATTERY|FUEL/PROPULSION|UNKNOWN',
    critical_re=r'FIRE|SMOKE|FLAME|BURN|THERMAL|MELT|SPARK|EXPLO|SWELL|OVERHEAT',
    qmin='2016Q1', qmax='2024Q4',
)
# 회계 쪽: 배터리사 '판매보증충당부채(또는 리콜 분담 충당부채) 분기 설정액'과 매출액을 prov 표(provision, revenue)로 넣으면 KEY3 동일 작동
