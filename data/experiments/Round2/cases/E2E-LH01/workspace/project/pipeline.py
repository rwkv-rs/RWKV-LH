def normalize(name):
    return name

def validate(record):
    return True

def price(record):
    return record['qty'] + record['unit_price']

def build_release(records):
    return {'items': records, 'grand_total': 0}
