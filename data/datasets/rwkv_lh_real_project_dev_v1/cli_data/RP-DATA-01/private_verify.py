"""Generate varied CSVs and verify reconciliation through CLI artifacts."""
import csv
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile


def main(workspace):
    workspace = Path(workspace).resolve()
    rng = random.Random(402918)
    cents = lambda text: Decimal(text).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    invoices = [{'invoice_id': f'inv-{index:03}', 'currency': ['USD','EUR','CNY'][index%3],
                 'amount': str(Decimal(rng.randrange(0,100000))/1000)} for index in range(37)]
    invoices[0]['amount'] = '1.005'
    valid_payments = []
    for index in range(83):
        invoice = invoices[rng.randrange(len(invoices))]
        valid_payments.append({'payment_id': f'pay-{index}', 'invoice_id': invoice['invoice_id'],
                               'currency': invoice['currency'], 'amount': str(Decimal(rng.randrange(-2000,20000))/1000)})
    invoices.extend([{'invoice_id':'free','currency':'USD','amount':'0'},
                     {'invoice_id':'unpaid','currency':'EUR','amount':'12.340'}])
    invalid_invoices = [{'invoice_id':'bad-amount','currency':'USD','amount':'NaN'},
                        {'invoice_id':'bad-currency','currency':'XXX','amount':'10'},
                        dict(invoices[0], amount='999')]
    invalid_payments = [dict(valid_payments[0], payment_id='missing', invoice_id='absent'),
                        dict(valid_payments[0], payment_id='currency', currency='EUR' if valid_payments[0]['currency'] != 'EUR' else 'USD'),
                        dict(valid_payments[0], payment_id='precision', amount='0.00001'),
                        dict(valid_payments[0], amount='888')]
    def write(path, fields, rows):
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    with tempfile.TemporaryDirectory(prefix='reconcile-private-') as raw:
        root = Path(raw)
        left, right, output = root/'invoices.csv', root/'payments.csv', root/'out'
        left_fields, right_fields = ['invoice_id','currency','amount'], ['payment_id','invoice_id','currency','amount']
        write(left, left_fields, invoices + [invoices[0]] + invalid_invoices)
        write(right, right_fields, valid_payments + [valid_payments[0]] + invalid_payments)
        def run(good=True):
            result = subprocess.run([sys.executable, str(workspace/'reconcile.py'), '--invoices', str(left), '--payments', str(right), '--output', str(output)],
                                    cwd=workspace, capture_output=True, text=True, timeout=30)
            assert (result.returncode == 0) == good, (result.returncode, result.stderr)
            return json.loads(result.stdout) if good else None
        summary = run()
        with (output/'reconciliation.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        expected, groups = [], {}
        for invoice in sorted(invoices, key=lambda row: row['invoice_id']):
            amount = cents(invoice['amount'])
            paid = sum((cents(payment['amount']) for payment in valid_payments if payment['invoice_id'] == invoice['invoice_id']), Decimal('0'))
            balance = amount-paid
            expected.append({'invoice_id': invoice['invoice_id'], 'currency': invoice['currency'], 'invoiced': f'{amount:.2f}',
                             'paid': f'{paid:.2f}', 'balance': f'{balance:.2f}',
                             'status': 'settled' if balance == 0 else 'underpaid' if balance > 0 else 'overpaid'})
            group = groups.setdefault(invoice['currency'], {'invoices':0,'invoiced':Decimal('0'),'paid':Decimal('0'),'balance':Decimal('0')})
            for field, value in [('invoices',1),('invoiced',amount),('paid',paid),('balance',balance)]:
                group[field] += value
        assert rows == expected, 'reconciliation amount/order/status mismatch'
        expected_summary = {'currencies': {key:{field:f'{value:.2f}' if isinstance(value,Decimal) else value for field,value in group.items()}
                                          for key,group in groups.items()}, 'duplicate_rows':2,'rejected_rows':7}
        assert summary == expected_summary
        assert json.loads((output/'summary.json').read_text()) == expected_summary
        with (output/'rejected.csv').open(newline='') as stream:
            rejects = list(csv.DictReader(stream))
        reasons = ['invalid_amount','invalid_currency','duplicate_id','unknown_invoice','currency_mismatch','invalid_amount','duplicate_id']
        locations = [('invoices', len(invoices)+3+i) for i in range(3)] + [('payments',len(valid_payments)+3+i) for i in range(4)]
        assert rejects == [{'source':source,'row':str(row),'reason':reason} for (source,row),reason in zip(locations,reasons)]
        first = {path.name:path.read_bytes() for path in output.iterdir()}
        assert run() == expected_summary
        assert {path.name:path.read_bytes() for path in output.iterdir()} == first, 'restart changed deterministic outputs'
        left.write_text('wrong,header\n1,2\n')
        run(good=False)
        assert {path.name:path.read_bytes() for path in output.iterdir()} == first, 'fatal import destroyed prior output'
        left.write_text('invoice_id,currency,amount\n"unterminated,USD,1\n')
        run(good=False)
        assert {path.name:path.read_bytes() for path in output.iterdir()} == first, 'malformed CSV destroyed prior output'
        write(left,left_fields,[])
        write(right,right_fields,[])
        assert run() == {'currencies':{},'duplicate_rows':0,'rejected_rows':0}
        with (output/'reconciliation.csv').open(newline='') as stream:
            assert list(csv.DictReader(stream)) == []
    print('reconciliation black-box acceptance passed')


if __name__ == '__main__':
    main(sys.argv[1])
