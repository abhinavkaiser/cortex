"""A deliberately modest lexical baseline. Improve it; do not edit labels."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent


def tokens(text):
    return set(re.findall(r'[a-z]+', text.lower()))


def retrieve(query, documents, k=2):
    scored = [(len(tokens(query) & tokens(d['text'])), d['id']) for d in documents if d['current']]
    return [doc_id for score, doc_id in sorted(scored, reverse=True)[:k] if score > 0]


def evaluate(split='dev'):
    docs = json.loads((ROOT / 'documents.json').read_text())
    cases = [q for q in json.loads((ROOT / 'questions.json').read_text()) if q['split'] == split]
    hits = total = 0
    for q in cases:
        found = retrieve(q['question'], docs)
        relevant = set(q['relevant'])
        if relevant:
            hits += len(relevant & set(found))
            total += len(relevant)
        print(json.dumps(dict(question=q['question'], expected=sorted(relevant), retrieved=found,
                              note='Abstain: no source answers this' if not relevant else 'Check evidence use separately')))
    print('Relevant documents found:', hits, '/', total)
    print('These exact counts on a tiny synthetic set do not estimate production accuracy.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true')
    evaluate('test' if parser.parse_args().test else 'dev')
