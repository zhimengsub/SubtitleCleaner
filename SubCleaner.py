import os
from argparse import RawTextHelpFormatter
import re
import traceback
import ass
from ass import Dialogue
from ass_tag_parser import parse_ass, AssText
from FullwidthConverter import MyParser, convertline, lookup

VER = 'v1.0.1'

DESCRIPTION = '字幕清理器\n' + \
              '把.ass文件中的对话部分提取出来，并进行半角片假名转换、多余符号清洗等各种操作\n' + \
              '—— ' + VER + ' by 谢耳朵w\n\n' + \
              '使用方法：将待转换文件拖放到本程序上即可，也可以使用命令行运行进行更多配置。\n\n' + \
              '详细介绍及最新版本请前往 https://github.com/barryZZJ/SubtitleCleaner 获取'

pats = [
    # remove …
    (re.compile(r'…'), ''),
    # remove 。(full width)
    (re.compile(r'。'), ''),
    # remove ｡
    (re.compile(r'｡'), ''),
    # remove ！
    (re.compile(r'！'), ''),
    # 顿号、改为半角空格
    (re.compile(r'、'), ' '),
    # remove (...)
    (re.compile(r'\(.*\)'), ''),
    # remove [...]
    (re.compile(r'\[.*\]'), ''),
    # remove \N
    (re.compile(r'\\N'), ''),
    # TODO \)\n替换成) ?
]  # type: list[tuple[re.Pattern, str]]

# add \N at each line's start
pats_final = [
    (re.compile(r'^'), r'\\N')
]  # type: list[tuple[re.Pattern, str]]

def initparser():
    parser = MyParser(description=DESCRIPTION, formatter_class=RawTextHelpFormatter)
    parser.add_argument('InputFile', type=str, help='待转换ass文件的路径。')
    parser.add_argument('-o', '--output', metavar='OUTFILE', type=str, help='输出文件名，默认为<输入文件名>_out.txt。')
    return parser

def mkOutfilename(infile: str):
    name, suf = os.path.splitext(infile)
    return name+'_out.txt'

def shouldMerge(event1:Dialogue, event2:Dialogue):
    if event1.text.endswith(r'…\N'):
        return 2
    if event1.start == event2.start and event1.end == event2.end:
        return 1
    return -1

def cleanline(line:str, pats:list[tuple[re.Pattern, str]]):
    for pat, repl in pats:
        line = pat.sub(repl, line)
    return line

def removeSFX(line:str):
    arr = parse_ass(line)
    texts = [a.text for a in arr if isinstance(a, AssText)]
    line = ''.join(texts)
    return line

def doclean(inname, outname, pats, lookup):
    encoding = 'utf-8-sig'
    outfile = None
    try:
        with open(inname, encoding=encoding) as f:
            doc = ass.parse(f)
        outfile = open(outname, 'w', encoding='utf-8')

        # merge lines by time and '…\N'
        cnter = 0
        j = 0
        i = 0
        mergedTexts = []
        print('合并台词中...\n')
        while i < len(doc.events):
            if doc.events[i].TYPE != 'Dialogue':
                i += 1
                continue
            otext = ntext = removeSFX(doc.events[i].text)
            # find events that should merge together
            j = i
            reasons = []
            while j+1 < len(doc.events) and (res:=shouldMerge(doc.events[j], doc.events[j+1])) > 0:
                cnter += 1
                if res == 1:
                    # same time, merge with half-width space
                    ntext = ntext + ' ' + removeSFX(doc.events[j+1].text)
                    reason = '(时间相同)'
                elif res == 2:
                    # ends with …\N, merge with full-width space
                    ntext = ntext + '　' + removeSFX(doc.events[j+1].text)
                    reason = r'(以…\N结尾)'
                else:
                    raise NotImplementedError('Merge result not implemented!')
                j += 1
                reasons.append(reason)
            if j != i:
                print(*reasons, otext, '->\n\t', ntext)
                print()
            mergedTexts.append(ntext)
            i = j + 1
        print('合并完毕！新并入了', cnter, '行对白。\n')

        # process line by line
        print('清理台词中...')
        cnter = 0
        for line in mergedTexts:
            cnter += 1
            # remove sfx codes
            # remove redundancies in line and convert halfwidth katakana
            nline = cleanline(line, pats)
            nline = convertline(nline, lookup)
            # 跳过空行
            if nline == '':
                print(line, '->')
                print()
                continue
            nline = cleanline(nline, pats_final)
            print(line, '->\n\t', nline)
            print()
            outfile.write(nline)
            outfile.write('\n')
        print('\n完成! 共处理了', cnter, '行对白，已保存至', outname)
        return True
    except Exception as err:
        print(
            '\n发生了未知错误！请将下面的报错信息及待转换文件提交到 https://github.com/barryZZJ/SubtitleCleaner/issues')
        traceback.print_exc()
        return False
    finally:
        if outfile:
            outfile.close()

def main():
    parser = initparser()
    args = parser.parse_args()
    print(DESCRIPTION)
    print()
    print('正在读取', args.InputFile)

    outname = args.output or mkOutfilename(args.InputFile)
    doclean(args.InputFile, outname, pats, lookup)

    print()
    os.system('pause')


if __name__ == '__main__':
    main()

