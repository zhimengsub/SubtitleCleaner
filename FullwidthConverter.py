import argparse
import os
import sys
import traceback
from argparse import RawTextHelpFormatter

VER = 'v1.0.1'

DESCRIPTION = '全角片假名转换器\n' + \
              '本程序可以将半角片假名/符号转换为全角形式\n' + \
              '—— ' + VER + ' by 谢耳朵w\n\n' + \
              '使用方法：将待转换文件拖放到本程序上即可，也可以使用命令行运行进行更多配置。\n\n' + \
              '最新版本请前往 https://github.com/barryZZJ/SubtitleCleaner 获取'

lookup = {
    '｡': '。', '｢': '「', '｣': '」', '､': '、', '･': '・',
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

class MyParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        print()
        args = {'prog': self.prog, 'message': message}
        sys.stderr.write(('%(prog)s: error: %(message)s\n') % args)
        os.system('pause')
        self.exit(2)

def initparser():
    parser = MyParser(description=DESCRIPTION, formatter_class=RawTextHelpFormatter)
    parser.add_argument('InputFile', type=str, help='待转换文本文件的路径，仅支持utf-8、GBK编码。')
    parser.add_argument('-o', '--output', metavar='OUTFILE', type=str, help='输出文件名，默认为<输入文件名>_out.txt。')
    return parser

def mkOutfilename(infile: str):
    name, suf = os.path.splitext(infile)
    return name+'_out'+suf

def convertline(line: str, lookup: dict):
    # 日字的数字、全角空格、全角标点符号不能改，可能还是改回查找表，并且额外增加浊音半浊音
    # line = unicodedata.normalize('NFKC', line)
    for old, new in lookup.items():
        line = line.replace(old, new)
    return line

def doconvert(inname, outname, lookup):
    cnter = 0
    encodings = ['utf-8-sig', 'gbk']
    infile = None
    outfile = None
    for encoding in encodings:
        try:
            infile = open(inname, 'r', encoding=encoding)
            outfile = open(outname, 'w', encoding=encoding)
            while line := infile.readline():
                nline = convertline(line, lookup)
                if nline != line:
                    cnter += 1
                    print(line.rstrip('\n'), '->\n\t', nline.rstrip('\n'))
                    print()
                outfile.write(nline)
            print('\n完成! 共转换了', cnter, '行，已保存至', outname)
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
    print(DESCRIPTION)
    print()
    print('正在读取', args.InputFile)

    outname = args.output or mkOutfilename(args.InputFile)
    doconvert(args.InputFile, outname, lookup)

    print()
    os.system('pause')
    #input('\nPress return to continue...')

if __name__ == '__main__':
    main()