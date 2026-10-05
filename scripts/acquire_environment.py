import argparse
from backend.acquisition import run

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Acquire bounded Thanjavur environmental context')
    parser.add_argument('--kinds',nargs='+',choices=['rainfall','soil','satellite','history'],default=['rainfall','soil','satellite','history'])
    parser.add_argument('--start-year',type=int,default=2024)
    parser.add_argument('--end-year',type=int,default=2025)
    args=parser.parse_args()
    if not 1984 <= args.start_year <= args.end_year <= 2025: parser.error('Use complete years between 1984 and 2025')
    run(args.kinds,args.start_year,args.end_year)
