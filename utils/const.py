import re
import sys
from pathlib import Path

from addict import Dict

ISEXE = hasattr(sys, 'frozen')
"""是否为打包程序"""

ROOT = Path(sys.executable).parent if ISEXE else Path(__file__).parents[1]
"""项目根路径"""

PATHS = Dict(
    CONF=ROOT / 'configs.json',  # 配置文件
)

# 一句话只有一位数字时改为全角
to_fullwidth = {'1': '１', '2': '２', '3': '３', '4': '４', '5': '５',
                '6': '６', '7': '７', '8': '８', '9': '９', '0': '０'}
to_halfwidth = {v: k for k, v in to_fullwidth.items()}
pat_single_digit = (re.compile(r'(?<!\d)\d(?!\d)'), lambda x: to_fullwidth.get(x.group(), x.group()))
pat_multi_digit = (re.compile(r'\d{2,}'), lambda x: ''.join(to_halfwidth.get(c, c) for c in x))

MERGE_SEP = '▒'
