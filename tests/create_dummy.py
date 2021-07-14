import sys
import argparse

import pandas as pd
import numpy as np

parser = argparse.ArgumentParser(description='Create dummy reference data.')
parser.add_argument('--items',
                    help='Input cscv with items. default: %(default)s',
                    metavar='<name>',
                    default='items.csv')
parser.add_argument('--case_ids',
                    help='Input txt with case ids. default: %(default)s',
                    metavar='<name>',
                    default='case_ids.txt')
parser.add_argument('--reference',
                    help='Output reference csv. default: %(default)s',
                    metavar='<name>',
                    default='reference.csv')

args = parser.parse_args()

df_items = pd.read_csv(args.items,
                       dtype=str,
                       keep_default_na=False,
                       na_values=[],
                       encoding='cp932')

with open(args.case_ids) as f:
    case_ids = f.read().splitlines()

data = np.random.randint(0, 100, (len(case_ids), len(df_items)))
df_ref = pd.DataFrame(data, columns=df_items['id'], index=case_ids)
df_ref.index.name = 'id'
df_ref.to_csv(args.reference, encoding='cp932')
