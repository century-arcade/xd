import sqlite3
import subprocess
import argparse

parser = argparse.ArgumentParser(description='Process some puzzles.')
parser.add_argument('-N', type=int, default=10, help='Number of iterations (default: 100)')
args = parser.parse_args()

N = args.N

conn = sqlite3.connect('gxd.sqlite')

cursor = conn.cursor()

sql_query = '''
SELECT b.xdid
FROM puzzles b
WHERE b.xdid NOT IN (SELECT xdid2 FROM gridmatches)
'''

for i in range(N):
    cursor.execute(sql_query)
    unchecked_puzzles = cursor.fetchall()
    print(f'{len(unchecked_puzzles)} puzzles remaining')
    if len(unchecked_puzzles) == 0:
        break

    process = subprocess.run('cat src/findmatches.sql | sqlite3 gxd.sqlite', shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

conn.close()
