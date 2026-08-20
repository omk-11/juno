import argparse
from src.controllers.server import start_server

def build_parser():
    parser=argparse.ArgumentParser(prog='juno')
    subparser=parser.add_subparsers(dest="actions", required=True)

    wake_parser=subparser.add_parser("wakeup")
    wake_parser.set_defaults(func=start_server)


    return parser

def main():
    parser = build_parser()
    args=parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()