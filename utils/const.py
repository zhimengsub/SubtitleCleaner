import re
import sys
from pathlib import Path

from addict import Dict
from bidict import bidict

ISEXE = hasattr(sys, 'frozen')
"""是否为打包程序"""

ROOT = Path(sys.executable).parent if ISEXE else Path(__file__).parents[1]
"""项目根路径"""

PATHS = Dict(
    CONF=ROOT / 'configs.json',  # 配置文件
)

# 标志台词需要合并的符号对
pairs = bidict({
    '《': '》',
    '<': '>',
    '＜': '＞',
    '〈': '〉',
    '「': '」',
    '｢': '｣',
    '『':'』',
    '(':')',
    '[':']',
})

# 标志以该符号结尾时与下一句台词合并
singlesufs = [
    '→'
]

# 清理相关
pats_rm = [
    # 删除符号
    (re.compile(r'\\N'), ''),
    (re.compile(r'…'), ''),
    (re.compile(r'。'), ''), (re.compile(r'｡'), ''),
    (re.compile(r'！'), ''), (re.compile(r'!'), ''),
    (re.compile(r'？'), ''), (re.compile(r'\?'), ''),
    (re.compile(r'~'), ''), (re.compile(r'～'), ''), (re.compile(r'∼'), ''),
    (re.compile(r'・'), ''),
    (re.compile(r'♪'), ''),
    (re.compile(r'≫'), ''),
    # 顿号、改为半角空格
    (re.compile(r'、'), ' '), (re.compile(r'､'), ' '),
    # 双引号改为单引号（取消）
    # (re.compile(r'『'), '「'), (re.compile(r'』'), '」'),
    # remove [...] 非贪婪模式，防止匹配[...]xxx[...]的形式
    (re.compile(r'\[.*?\]'), ''),
]  # type: list[tuple[re.Pattern, str]]

pats_rmcomment = [
    # remove (...) 非贪婪模式，防止匹配(...)xxx(...)的形式
    (re.compile(r'\(.*?\)'), ''),
]  # type: list[tuple[re.Pattern, str]]

pats_rmpairs = [
    # 删除成对的符号
    (re.compile(r'《'), ''), (re.compile(r'》'), ''),
    (re.compile(r'<'), ''), (re.compile(r'＜'), ''), (re.compile(r'〈'), ''),
    (re.compile(r'>'), ''), (re.compile(r'＞'), ''), (re.compile(r'〉'), ''),
    # remove [...] 非贪婪模式，防止匹配[...]xxx[...]的形式
    (re.compile(r'\[.*?\]'), ''),
]

pats_stripsuf = [
    # 删除结尾单符号合并标志
    (re.compile(c + '$'), '') for c in singlesufs
]

# 拟声词 v0.2
mainpats = [
    'ん',
    'うむ', 'ええ', 'わあ', 'うわ',
    'あぁ', 'はぁ', 'うわぁ',
    'んっ', 'うっ', 'よっ', 'はっ', 'ひっ', 'ほっ', 'あっ', 'えっ', 'なっ', 'わっ',
    'えへへへ',
    'あ+?',
    'う+?',
    'は{2,}',
    '(?:うん)+',
]

pats_ono = [
    (re.compile(r' ' + pat + r' '), ' ') for pat in mainpats  # 前后都有空格的话，清理后需保留一个空格
] + [
    (re.compile(r'(?:^| )' + pat + r'(?: |$)'), '') for pat in mainpats
]
# type: list[tuple[re.Pattern, str]]


# 对合并后的每一行进行处理
pats_prefix = [
    # 添加\N
    (re.compile(r'(^|\n)'), r'\1\\N'),
]  # type: list[tuple[re.Pattern, str]]

pats_final = [
    # 多个半角空格缩至一个
    (re.compile(r' +'), ' '),

]  # type: list[tuple[re.Pattern, str]]

# 一句话只有一位数字时改为全角
to_fullwidth = {'1': '１', '2': '２', '3': '３', '4': '４', '5': '５',
                '6': '６', '7': '７', '8': '８', '9': '９', '0': '０'}
to_halfwidth = {v: k for k, v in to_fullwidth.items()}
pat_single_digit = (re.compile(r'(?<!\d)\d(?!\d)'), lambda x: to_fullwidth.get(x.group(), x.group()))
pat_multi_digit = (re.compile(r'\d{2,}'), lambda x: ''.join(to_halfwidth.get(c, c) for c in x))

MERGE_SEP = '▒'
