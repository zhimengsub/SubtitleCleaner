import os
import traceback
from argparse import RawTextHelpFormatter
from pathlib import Path
from typing import Union

from utils.argparser import MyParser
from utils.logfile import _print, setLogfile, closeLogfile, print
from utils.misc import mkFilepath

VER = 'v1.0.4_halfwidth-sp'

DESCRIPTION = '全角片假名转换器\n' + \
              '本程序可以将半角片假名与｡ ｢ ｣ ､ ･等符号转换为全角形式，并将全角数字、空格转换为半角形式\n' + \
              '—— ' + VER + ' by 谢耳朵w\n\n' + \
              '使用方法：将待转换文件拖放到本程序上即可，也可以使用命令行运行进行更多配置。\n\n' + \
              '详细介绍、获取最新版本、提交建议和bug请前往 https://github.com/barryZZJ/SubtitleCleaner'

lookup = {
    '１': '1', '２': '2', '３': '3', '４': '4', '５': '5',
    '６': '6', '７': '7', '８': '8', '９': '9', '０': '0',
    '｡': '。', '｢': '「', '｣': '」', '､': '、', '･': '・', '　': ' ',
    'ｶﾞ': 'ガ', 'ｷﾞ': 'ギ', 'ｸﾞ': 'グ', 'ｹﾞ': 'ゲ', 'ｺﾞ': 'ゴ',
    'ｻﾞ': 'ザ', 'ｼﾞ': 'ジ', 'ｽﾞ': 'ズ', 'ｾﾞ': 'ゼ', 'ｿﾞ': 'ゾ',
    'ﾀﾞ': 'ダ', 'ﾁﾞ': 'ヂ', 'ﾂﾞ': 'ヅ', 'ﾃﾞ': 'デ', 'ﾄﾞ': 'ド',
    'ﾊﾞ': 'バ', 'ﾋﾞ': 'ビ', 'ﾌﾞ': 'ブ', 'ﾍﾞ': 'ベ', 'ﾎﾞ': 'ボ',
    'ﾊﾟ': 'パ', 'ﾋﾟ': 'ピ', 'ﾌﾟ': 'プ', 'ﾍﾟ': 'ペ', 'ﾎﾟ': 'ポ',
    'ｧ': 'ァ', 'ｨ': 'ィ', 'ｩ': 'ゥ', 'ｪ': 'ェ', 'ｫ': 'ォ',
    'ｬ': 'ャ', 'ｭ': 'ュ', 'ｮ': 'ョ', 'ｯ': 'ッ', 'ｰ': 'ー',
    'ｱ': 'ア', 'ｲ': 'イ', 'ｳ': 'ウ', 'ｴ': 'エ', 'ｵ': 'オ',
    'ｶ': 'カ', 'ｷ': 'キ', 'ｸ': 'ク', 'ｹ': 'ケ', 'ｺ': 'コ',
    'ｻ': 'サ', 'ｼ': 'シ', 'ｽ': 'ス', 'ｾ': 'セ', 'ｿ': 'ソ',
    'ﾀ': 'タ', 'ﾁ': 'チ', 'ﾂ': 'ツ', 'ﾃ': 'テ', 'ﾄ': 'ト',
    'ﾅ': 'ナ', 'ﾆ': 'ニ', 'ﾇ': 'ヌ', 'ﾈ': 'ネ', 'ﾉ': 'ノ',
    'ﾊ': 'ハ', 'ﾋ': 'ヒ', 'ﾌ': 'フ', 'ﾍ': 'ヘ', 'ﾎ': 'ホ',
    'ﾏ': 'マ', 'ﾐ': 'ミ', 'ﾑ': 'ム', 'ﾒ': 'メ', 'ﾓ': 'モ',
    'ﾔ': 'ヤ', 'ﾕ': 'ユ', 'ﾖ': 'ヨ',
    'ﾗ': 'ラ', 'ﾘ': 'リ', 'ﾙ': 'ル', 'ﾚ': 'レ', 'ﾛ': 'ロ',
    'ﾜ': 'ワ', 'ﾝ': 'ン', 'ｦ': 'ヲ',
}

def initparser():
    parser = MyParser(description=DESCRIPTION, formatter_class=RawTextHelpFormatter)
    parser.add_argument('InputFile', type=str, help='待转换文本文件的路径，仅支持utf-8、GBK编码。')
    parser.add_argument('-o', '--output', metavar='OUTFILE', type=str, help='输出文件名，默认为<输入文件名>_out.txt。')
    parser.add_argument('-q', '--quit', action='store_true', help='结束后不暂停程序直接退出，方便命令行调用。不加该参数程序结束时会暂停。')
    parser.add_argument('--log', action='store_true', help='记录日志，执行结果输出到<输入文件名>_log.txt')
    return parser

def convertline(line: str, lookup: dict):
    # 日字的数字、全角空格、全角标点符号不能改，可能还是改回查找表，并且额外增加浊音半浊音
    # 不能用str.translate，因为带浊音的假名是两个字符
    # line = unicodedata.normalize('NFKC', line)
    for old, new in lookup.items():
        line = line.replace(old, new)
    return line

def doconvert(inpath, outpath: Union[str, Path], lookup):
    cnter = 0
    encodings = ['utf-8-sig', 'gbk']
    infile = None
    outfile = None
    for encoding in encodings:
        try:
            infile = open(inpath, 'r', encoding=encoding)
            outfile = open(outpath, 'w', encoding=encoding)
            while line := infile.readline():
                nline = convertline(line, lookup)
                if nline != line:
                    cnter += 1
                    print(line.rstrip('\n'), '->\n\t', nline.rstrip('\n'))
                    print()
                outfile.write(nline)
            print('\n完成! 共转换了', cnter, '行，已保存至', str(outpath))
            return True
        except UnicodeDecodeError:
            continue
        except Exception as err:
            print('\n发生了未知错误！请将下面的报错信息及待转换文件提交到 https://github.com/barryZZJ/SubtitleCleaner/issues\n')
            traceback.print_exc()
            return False
        finally:
            if infile:
                infile.close()
            if outfile:
                outfile.close()

    print('\n错误！无法识别的文件编码，请将文件转存为UTF8或GBK编码格式再试！')
    return False

def main():
    parser = initparser()
    args = parser.parse_args()
    if args.log:
        logpath = mkFilepath(args.InputFile, '.txt', '_log')
        setLogfile(logpath)
    try:
        print(DESCRIPTION)
        print()
        print('正在读取', args.InputFile)

        outname = args.output or mkFilepath(args.InputFile, 'txt')
        doconvert(args.InputFile, outname, lookup)

        print()
    except Exception as err:
        print(
            '\n发生了未知错误！请将下面的报错信息及待转换文件提交到 https://github.com/barryZZJ/SubtitleCleaner/issues')
        traceback.print_exc()
    finally:
        if args.log:
            closeLogfile()
            _print('日志文件已保存至', str(logpath))
            _print()

        if not args.quit:
            os.system('pause')

if __name__ == '__main__':
    main()