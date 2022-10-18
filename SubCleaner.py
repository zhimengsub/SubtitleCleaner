import os
from argparse import RawTextHelpFormatter
import re
import traceback
import ass
from ass import Dialogue
from ass_tag_parser import parse_ass, AssText
from FullwidthConverter import MyParser, convertline, lookup

VER = 'v2.3.1'

DESCRIPTION = '字幕清理器\n' + \
              '输入.ass字幕文件，提取对话文本，进行台词合并、清理、假名转换后输出为文本文件\n' + \
              '—— ' + VER + ' by 谢耳朵w\n\n' + \
              '使用方法：将待转换文件拖放到本程序上即可，也可以使用命令行运行进行更多配置。\n\n' + \
              '详细介绍、获取最新版本、提交建议和bug请前往 https://github.com/zhimengsub/SubtitleCleaner'

# 标志台词需要合并的符号对
pairs = {
    '《': '》',
    '<': '>',
    '＜': '＞',
    '〈': '〉',
    '「': '」',
    '｢': '｣',
}

single_end = [
    '→'
]

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
    # remove '→'
    (re.compile(r'→'), ''),
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
    '''
    return:
        res:int >=0, 需要合并； <0, 不合并
        symbol:str
            当res in [1, 2]时，为mergeLSymb: 匹配到的成对标识符的开头
            当res in [-2, 3]时，为singleSymb: 匹配到的单个标识符
    '''
    if not mergeLSymb:
        # 先找有没有成对标识符
        # look for left symbol
        for l, r in pairs.items():
            if l in event1.text and r not in event1.text:
                mergeLSymb = l
                break
    if mergeLSymb:
        # 有成对标识符就只匹配标识符
        # look for right symbol
        if mergeLSymb in event1.text and pairs[mergeLSymb] not in event1.text:
            if pairs[mergeLSymb] in event2.text:
                return 2, mergeLSymb  # 拼接结束
            else:
                return 1, mergeLSymb  # 继续拼接

    # 找单个标识符
    for symb in single_end:
        if event1.text.endswith(symb+r'\N'):
            return 3, symb
        elif symb in event1.text:
            return -2, symb

    # # 没找到标识符，则匹配时间
    # if event1.start == event2.start and event1.end == event2.end:
    #     return 0, ''

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
    warnings = []
    try:
        with open(inname, encoding=encoding) as f:
            doc = ass.parse(f)
        outfile = open(outname, 'w', encoding='utf-8')

        cnter_mg = 0
        cnter_cv = 0
        procid = 0  # number of processed lines
        i = 0
        print('开始处理字幕...\n')
        while i < len(doc.events):
            if doc.events[i].TYPE != 'Dialogue' or doc.events[i].style.lower() == 'rubi':
                if doc.events[i].style.lower() == 'rubi':
                    print('[跳过Rubi台词]')
                    print(removeSFX(doc.events[i].text))
                    print()
                i += 1
                continue
            procid += 1
            oline = removeSFX(doc.events[i].text)
            nline = cleanline(removeSFX(doc.events[i].text), pats)

            # merge and clean lines
            j = i
            reason = ''
            ret = (-10, '')
            mergeLeftSymb = ''  # 已匹配到的合并标志对左符号
            eventL = doc.events[i]
            while j+1 < len(doc.events) and (ret:=shouldMerge(eventL, doc.events[j+1], mergeLeftSymb))[0] >= 0:
                res, symbol = ret
                j += 1
                oline += ' + ' + removeSFX(doc.events[j].text)
                nextline = cleanline(removeSFX(doc.events[j].text), pats)
                if not nextline: continue
                sep = '　'  # 全角空格
                if res == 1:
                    # 匹配到符号对，且继续拼接
                    mergeLeftSymb = symbol
                    if not reason:
                        reason = f"[合并](以'{mergeLeftSymb}'开头)(尚未发现'{pairs[mergeLeftSymb]}')"
                    else:
                        reason += f"(尚未发现'{pairs[mergeLeftSymb]}')"
                elif res == 2:
                    # 匹配到符号对，且拼接结束
                    mergeLeftSymb = symbol
                    if not reason:
                        reason = f"[合并](以'{mergeLeftSymb}'开头)(以'{pairs[mergeLeftSymb]}'结尾)"
                    else:
                        reason += f"(以'{pairs[mergeLeftSymb]}'结尾)"
                    # 考虑到存在下一行时间仍相同，或者出现新的标识符的情况，故继续搜索
                    eventL = doc.events[j]
                    mergeLeftSymb = ''
                elif res == 3:
                    # 匹配到单个符号结尾
                    singleSymb = symbol
                    if not reason:
                        reason = f"[合并](以'{singleSymb}'结尾)"
                    else:
                        reason += f"(以'{singleSymb}'结尾)"
                    eventL = doc.events[j]
                    mergeLeftSymb = ''
                # elif res == 0:
                #     # same time, merge with half-width space
                #     if not reason:
                #         reason = '[合并](时间相同)(时间相同)'
                #     else:
                #         reason += '(时间相同)'
                #     mergeLeftSymb = ''
                #     sep = ' '
                else:
                    raise NotImplementedError('Merge result not implemented!')
                nline = nline + sep + nextline
            # merge done
            res, symbol = ret
            if j != i:
                # did merge, print msg
                # 再次清理一遍，因为有可能合并过后产生新的成对括号等符合清理条件的内容
                nline = cleanline(nline, pats)
                # j为最后一条发生merge的行数
                if res == 1:
                    warn = f"WARNING: 未找到配对的'{pairs[symbol]}'，请手动修改ass文件使左右标志符号个数一致！"
                    print(warn)
                    warnings.append((procid, warn))
                cnter_mg += j - i + 1
                print(reason)
            if res == -2:
                # 匹配单个符号，但不在句尾
                warn = f"WARNING: 找到符号'{symbol}'，但不在句尾，如需合并请手动修改！"
                print(warn)
                warnings.append((procid, warn))

            # convert half-width katakana and symbols
            nline_cv = convertline(nline, lookup)
            if nline_cv != nline:
                reason = '[转换假名]'
                print(reason)
                cnter_cv += 1
            # convert done

            if nline_cv == '':
                print(str(procid)+'.', oline, '-> <删除该行>')
            else:
                print(str(procid)+'.', oline, '->\n\t', nline_cv)
                # add \N at start
                nline_cv = cleanline(nline_cv, pats_final)
                outfile.write(nline_cv)
                outfile.write('\n')

            print()
            i = j + 1

        print('处理完成！共合并了', cnter_mg, '行对白，假名转换了', cnter_cv, '行对白，最终生成了', procid, '行对白。')
        print('\n已保存至', outname)

        if len(warnings):
            print('\n存在WARNING，请根据下方信息向上查找对应记录')
            for procid, msg in warnings:
                print('\t第' + str(procid) + '条:', msg)

        return True
    except Exception as err:
        print(
            '\n发生了未知错误！请将下面的报错信息及待转换文件提交到 https://github.com/zhimengsub/SubtitleCleaner/issues')
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
            '\n发生了未知错误！请将下面的报错信息及待转换文件提交到 https://github.com/zhimengsub/SubtitleCleaner/issues')
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

