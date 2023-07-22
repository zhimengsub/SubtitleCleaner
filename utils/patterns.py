import re

from bidict import bidict


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
pats_stripsuf: list[tuple[re.Pattern, str]] = [
    # 删除结尾单符号合并标志
    (re.compile(c + '$'), '') for c in singlesufs
]
pats_rm: list[tuple[re.Pattern, str]] = [
    # 删除换行
    (re.compile(r'\\N'), ''),
    # 双引号改为单引号（取消）
    # (re.compile(r'『'), '「'), (re.compile(r'』'), '」'),
    # remove [...] 非贪婪模式，防止匹配[...]xxx[...]的形式
    (re.compile(r'\[.*?\]'), ''),
]
pats_rmcomment: list[tuple[re.Pattern, str]] = [
    # remove (...) 非贪婪模式，防止匹配(...)xxx(...)的形式
    (re.compile(r'\(.*?\)'), ''),
]
pats_rmpairs: list[tuple[re.Pattern, str]] = [
    # remove [...] 非贪婪模式，防止匹配[...]xxx[...]的形式
    (re.compile(r'\[.*?\]'), ''),
]


def load_patterns_from_conf(conf):
    global pats_rm
    # 删除符号
    if conf.symbols.remove != '':
        pats_rm.append(
            (re.compile('[' + conf.symbols.remove + ']'), ''),
        )
    # 替换符号
    if conf.symbols.replace_key != '' and conf.symbols.replace_val != '':
        assert len(conf.symbols.replace_key) == len(conf.symbols.replace_val),\
            'symbols.replace_key的个数与symbols.replace_val的个数不一致！'
        pats_rm.extend(
            (re.compile(string), repl)
            for string, repl in
            zip(conf.symbols.replace_key, conf.symbols.replace_val)
        )


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

pats_ono: list[tuple[re.Pattern, str]] = [
    (re.compile(r' ' + pat + r' '), ' ') for pat in mainpats  # 前后都有空格的话，清理后需保留一个空格
] + [
    (re.compile(r'(?:^| )' + pat + r'(?: |$)'), '') for pat in mainpats
]

pats_prefix: list[tuple[re.Pattern, str]] = [
    # 添加\N
    (re.compile(r'(^|\n)'), r'\1\\N'),
]

# 对合并后的每一行进行处理
pats_final: list[tuple[re.Pattern, str]] = [
    # 多个半角空格缩至一个
    (re.compile(r' +'), ' '),

]
