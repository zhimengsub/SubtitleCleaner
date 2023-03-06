_LOGFILE = None
_print = print


def setLogfile(path):
    global _LOGFILE
    _LOGFILE = open(path, 'w', encoding='utf8')


def closeLogfile():
    if _LOGFILE is not None:
        _LOGFILE.close()


def print(*args, **kwargs):
    _print(*args, **kwargs)
    if _LOGFILE is not None:
        _print(*args, **kwargs, file=_LOGFILE)

def warning(*args, **kwargs):
    print('WARNING:', *args, **kwargs)

def error(*args, **kwargs):
    print('ERROR:', *args, **kwargs)