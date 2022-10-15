import os
from argparse import RawTextHelpFormatter
import re
import traceback
import ass
from ass import Dialogue
from ass_tag_parser import parse_ass, AssText
from FullwidthConverter import MyParser, convertline, lookup

VER = 'v2.1.0'

DESCRIPTION = '字幕清理器\n' + \
              '输入.ass字幕文件，提取对话文本，进行台词合并、清理、假名转换后输出为文本文件\n' + \
              '—— ' + VER + ' by 谢耳朵w\n\n' + \
              '使用方法：将待转换文件拖放到本程序上即可，也可以使用命令行运行进行更多配置。\n\n' + \
              '详细介绍、获取最新版本、提交建议和bug请前往 https://github.com/barryZZJ/SubtitleCleaner'

# 标志台词需要合并的符号对
pairs = {
    '《': '》',
    '<': '>',
    '＜': '＞',
    '〈': '〉',
    '「': '」',
    '｢': '｣',
}

pats = [
    # remove …
    (re.compile(r'…'), ''),
    # remove 。(full width)
    (re.compile(r'。'), ''),
    # remove ｡
    (re.compile(r'｡'), ''),
    # remove ！
    (re.compile(r'！'), ''),
    # remove 《
    (re.compile(r'《'), ''),
    # remove 》
    (re.compile(r'》'), ''),
    # remove <
    (re.compile(r'<'), ''),
    (re.compile(r'＜'), ''),
    (re.compile(r'〈'), ''),
    # remove >
    (re.compile(r'>'), ''),
    (re.compile(r'＞'), ''),
    (re.compile(r'〉'), ''),
    # remove ~
    (re.compile(r'~'), ''),
    (re.compile(r'～'), ''),
    (re.compile(r'∼'), ''),
    # 顿号、改为半角空格
    (re.compile(r'、'), ' '),
    (re.compile(r'､'), ' '),
    # remove (...) 非贪婪模式，防止匹配(...)xxx(...)的形式
    (re.compile(r'\(.*?\)'), ''),
    # remove [...] 非贪婪模式，防止匹配[...]xxx[...]的形式
    (re.compile(r'\[.*?\]'), ''),
    # remove \N
    (re.compile(r'\\N'), ''),
]  # type: list[tuple[re.Pattern, str]]

# add \N at each line's start
pats_final = [
    (re.compile(r'^'), r'\\N')
]  # type: list[tuple[re.Pattern, str]]

oldprint = print
logfile = None
def print(*args, **kwargs):
    oldprint(*args, **kwargs)
    if logfile:
        oldprint(*args, **kwargs, file=logfile)

def initparser():
    parser = MyParser(description=DESCRIPTION, formatter_class=RawTextHelpFormatter)
    parser.add_argument('InputFile', type=str, help='待转换ass文件的路径。')
    parser.add_argument('-o', '--output', metavar='OUTFILE', type=str, help='输出文件名，默认为<输入文件名>.txt。')
    parser.add_argument('-q', '--quit', action='store_true', help='结束后不暂停程序直接退出，方便命令行调用。不加该参数程序结束时会暂停。')
    parser.add_argument('--log', action='store_true', help='记录日志，执行结果输出到<输入文件名>_log.txt')
    return parser

def mkOutfilename(infile: str, namesuf=''):
    name, suf = os.path.splitext(infile)
    return name+namesuf+'.txt'

def shouldMerge(event1:Dialogue, event2:Dialogue, mergeLSymb='') -> tuple[int, str]:

    if not mergeLSymb:
        # 先找有没有标识符
        # look for left symbol
        for l, r in pairs.items():
            if l in event1.text and r not in event1.text:
                mergeLSymb = l
                break
    if mergeLSymb:
        # 有标识符就只匹配标识符，不匹配时间
        # look for right symbol
        if mergeLSymb in event1.text and pairs[mergeLSymb] not in event1.text:
            if pairs[mergeLSymb] in event2.text:
                return 2, mergeLSymb  # 拼接结束
            else:
                return 1, mergeLSymb  # 继续拼接
    # 没找到标识符，则匹配时间
    if event1.start == event2.start and event1.end == event2.end:
        return 0, ''

    # 都不符合，不merge
    return -1, ''

def cleanline(line:str, pats:list[tuple[re.Pattern, str]]):
    for pat, repl in pats:
        line = pat.sub(repl, line)
    line = line.strip(' 　')
    return line

def removeSFX(line:str):
    arr = parse_ass(line)
    texts = [a.text for a in arr if isinstance(a, AssText)]
    line = ''.join(texts)
    return line

def doclean(inname, outname, pats, lookup):
    encoding = 'utf-8-sig'
    outfile = None
    warnings_mergeclean = []
    warnings_convert = []
    try:
        with open(inname, encoding=encoding) as f:
            doc = ass.parse(f)
        outfile = open(outname, 'w', encoding='utf-8')

        # 台词合并与清理
        cnter = 0
        procid = 1  # number of processed lines
        i = 0
        mergedCleanLines = []
        print('合并与清理台词中...\n')
        while i < len(doc.events):
            if doc.events[i].TYPE != 'Dialogue':
                i += 1
                continue
            oline = removeSFX(doc.events[i].text)
            nline = cleanline(removeSFX(doc.events[i].text), pats)
            # find events that should merge together
            j = i
            reason = ''
            res = -1
            mergeLeftSymbol = ''  # 已匹配到的合并标志开头符号
            eventL = doc.events[i]
            while j+1 < len(doc.events) and (ret:=shouldMerge(eventL, doc.events[j+1], mergeLeftSymbol))[0] >= 0:
                res, mergeLeftSymbol = ret
                j += 1
                oline += ' + ' + removeSFX(doc.events[j].text)
                nextline = cleanline(removeSFX(doc.events[j].text), pats)
                if not nextline: continue
                nline = nline + '　' + nextline
                if res == 1:
                    # 继续拼接
                    if not reason:
                        reason = f"[合并](以'{mergeLeftSymbol}'开头)(尚未发现'{pairs[mergeLeftSymbol]}')"
                    else:
                        reason += f"(尚未发现'{pairs[mergeLeftSymbol]}')"
                elif res == 2:
                    # 拼接结束
                    if not reason:
                        reason = f"[合并]('{mergeLeftSymbol}'开头)(以'{pairs[mergeLeftSymbol]}'结尾)"
                    else:
                        reason += f"(以'{pairs[mergeLeftSymbol]}'结尾)"
                    # 考虑到存在下一行时间仍相同，或者出现新的标识符的情况，故继续搜索
                    eventL = doc.events[j]
                    mergeLeftSymbol = ''
                elif res == 0:
                    # same time, merge with half-width space
                    if not reason:
                        reason = '[合并](时间相同)(时间相同)'
                    else:
                        reason += '(时间相同)'
                    mergeLeftSymbol = ''
                else:
                    raise NotImplementedError('Merge result not implemented!')

            # merge done
            # 再次清理一遍，因为有可能合并过后产生新的成对括号等符合清理条件的内容
            nline = cleanline(nline, pats)
            if j != i:
                # j为最后一条发生merge的行数
                # did merge
                if res == 1:
                    warn = f"WARNING: 未找到配对的'{pairs[mergeLeftSymbol]}'，请手动修改ass文件使左右标志符号个数一致！"
                    print(warn)
                    warnings_mergeclean.append((procid, warn))
                cnter += j - i + 1
                print(reason)

            if nline == '':
                print(str(procid)+'.', oline, '-> <删除该行>')
            else:
                print(str(procid)+'.', oline, '->\n\t', nline)
                nline = cleanline(nline, pats_final)
                mergedCleanLines.append(nline)
            print()
            procid += 1
            i = j + 1

        print('合并与清理阶段完成！共合并了', cnter, '行对白，共生成了', procid, '行对白。')
        # todo 把转换假名合并到上面的步骤，分开统计信息
        # process line by line
        print('\n' + '=' * 50 + '\n\n转换半角假名中...')
        cnter = 0
        procid = 0
        for line in mergedCleanLines:
            # convert half-width katakana and symbols
            nline = convertline(line, lookup)
            if nline != line:
                procid += 1
                cnter += 1
                print(str(procid)+'.', line, '->\n\t', nline)
                print()
            outfile.write(nline)
            outfile.write('\n')
        print('假名转换阶段完成! 共处理了', cnter, '行对白')
        print('\n已保存至', outname)

        if len(warnings_mergeclean):
            print('\n合并与清理阶段存在WARNING，请根据下方信息向上查找对应记录')
            for procid, msg in warnings_mergeclean:
                print('\t第' + str(procid) + '条:', msg)

        if len(warnings_convert):
            print('\n假名转换阶段存在WARNING，请根据下方信息向上查找对应记录')
            for procid, msg in warnings_convert:
                print('\t第' + str(procid) + '条:', msg)

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
    global logfile
    parser = initparser()
    args = parser.parse_args()
    if args.log:
        logfile = open(mkOutfilename(args.InputFile, '_log'), 'w', encoding='utf-8')
    try:
        print(DESCRIPTION)
        print()
        print('正在读取', args.InputFile)
        outname = args.output or mkOutfilename(args.InputFile)
        doclean(args.InputFile, outname, pats, lookup)
        print()
    except Exception as err:
        print(
            '\n发生了未知错误！请将下面的报错信息及待转换文件提交到 https://github.com/barryZZJ/SubtitleCleaner/issues')
        traceback.print_exc()
    finally:
        if logfile:
            logfile.close()
            oldprint('日志文件已保存至', mkOutfilename(args.InputFile, '_log'))
            oldprint()

        if not args.quit:
            os.system('pause')


if __name__ == '__main__':
    main()

