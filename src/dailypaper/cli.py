import argparse
from .pipeline import run_for_date, show_for_date, run_yesterday, show_yesterday

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("run-yesterday")
    p2 = sub.add_parser("show-yesterday")

    p3 = sub.add_parser("run")
    p3.add_argument("date", help="YYYY-MM-DD")

    p4 = sub.add_parser("show")
    p4.add_argument("date", help="YYYY-MM-DD")

    args = ap.parse_args()

    if args.cmd == "run-yesterday":
        run_yesterday()
    elif args.cmd == "show-yesterday":
        show_yesterday()
    elif args.cmd == "run":
        run_for_date(args.date)
    elif args.cmd == "show":
        show_for_date(args.date)

if __name__ == "__main__":
    main()
