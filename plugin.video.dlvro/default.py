import sys
from urllib.parse import parse_qsl
from resources.lib.main import router

if __name__ == '__main__':
    router(dict(parse_qsl(sys.argv[2][1:])))