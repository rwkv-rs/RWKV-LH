def normalize(name): return name

def validate(item): return True

def total(item): return item['quantity'] + item['price']

def build(items): return {'items': items, 'grand_total': 0}
