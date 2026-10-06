import json, sys
topo = sys.argv[1]
kept = 0
with open('ft_dataset/train.jsonl', encoding='utf-8') as fh, open(f'ft_dataset/train_no_{topo}.jsonl', 'w', encoding='utf-8') as out:
    for line in fh:
        if json.loads(line)['topology'] != topo:
            out.write(line); kept += 1
print(f'{kept} rows -> ft_dataset/train_no_{topo}.jsonl (rename to train.jsonl in a copied FT_DATA_DIR)')
