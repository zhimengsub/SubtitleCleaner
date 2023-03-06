import os
import sys
import argparse

from utils.logfile import print


class MyParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        print()
        args = {'prog': self.prog, 'message': message}
        sys.stderr.write(('%(prog)s: error: %(message)s\n') % args)
        os.system('pause')
        self.exit(2)
