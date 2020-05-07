import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')
django.setup()
from run_init import *

with open('./data/products.json') as f:
    products = json.load(f)
from pyquery import PyQuery as pq

count = 0
ret = []
for pd in products:
    if not pd:
        count += 1
        print('not pd', count)
        continue
    doc = pd['product_info']
    dom = pq(doc)
    for el in dom('p.strong'):
        text_len = len(el.text)
        if not text_len % 2 == 0:
            continue
        text = el.text
        if text[:int(text_len / 2)] == text[int(text_len / 2):]:
            print(text[:int(text_len / 2)])
            el.text(text[:int(text_len / 2)])
    pd['product_info'] = dom.html()
    el = pd
    ret.append(el)

print()
with open('./data/products.json', 'w') as f:
    f.write(json.dumps(ret))
