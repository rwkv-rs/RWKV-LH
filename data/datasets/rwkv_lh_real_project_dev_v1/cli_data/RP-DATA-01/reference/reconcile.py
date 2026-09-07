"""Reconcile independent invoice and payment CSV exports using decimal money."""
import argparse
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def money(value):
    try:
        result = Decimal(value)
        if not result.is_finite() or result.as_tuple().exponent < -4:
            raise ValueError('invalid_amount')
        return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError('invalid_amount')


def read_rows(path, columns):
    with open(path, newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames != columns:
            raise ValueError('invalid CSV header')
        return list(reader)


def reconcile(invoice_path, payment_path, output):
    invoice_rows = read_rows(invoice_path, ['invoice_id', 'currency', 'amount'])
    payment_rows = read_rows(payment_path, ['payment_id', 'invoice_id', 'currency', 'amount'])
    invoices, payments, rejected = {}, {}, []
    duplicates = 0
    for source, rows in [('invoices', invoice_rows), ('payments', payment_rows)]:
        for row_number, row in enumerate(rows, 2):
            try:
                if None in row or any(value is None or not value.strip() for value in row.values()):
                    raise ValueError('missing_fields')
                if row['currency'] not in {'USD', 'EUR', 'CNY'}:
                    raise ValueError('invalid_currency')
                amount = money(row['amount'])
                if source == 'invoices' and Decimal(row['amount']) < 0:
                    raise ValueError('invalid_amount')
                key = row['invoice_id'] if source == 'invoices' else row['payment_id']
                value = (row['currency'], amount) if source == 'invoices' else (row['invoice_id'], row['currency'], amount)
                table = invoices if source == 'invoices' else payments
                if key in table:
                    if table[key] != value:
                        raise ValueError('duplicate_id')
                    duplicates += 1
                    continue
                if source == 'payments':
                    if row['invoice_id'] not in invoices:
                        raise ValueError('unknown_invoice')
                    if invoices[row['invoice_id']][0] != row['currency']:
                        raise ValueError('currency_mismatch')
                table[key] = value
            except ValueError as error:
                rejected.append({'source': source, 'row': row_number, 'reason': str(error)})
    totals = {key: Decimal('0.00') for key in invoices}
    for invoice, currency, amount in payments.values():
        totals[invoice] += amount
    lines, currencies = [], {}
    for key, (currency, amount) in sorted(invoices.items()):
        paid, balance = totals[key], amount - totals[key]
        lines.append({'invoice_id': key, 'currency': currency, 'invoiced': f'{amount:.2f}', 'paid': f'{paid:.2f}',
                      'balance': f'{balance:.2f}', 'status': 'settled' if balance == 0 else 'underpaid' if balance > 0 else 'overpaid'})
        group = currencies.setdefault(currency, {'invoices': 0, 'invoiced': Decimal('0.00'), 'paid': Decimal('0.00'), 'balance': Decimal('0.00')})
        group['invoices'] += 1
        group['invoiced'] += amount
        group['paid'] += paid
        group['balance'] += balance
    summary = {'currencies': {key: {field: f'{value:.2f}' if isinstance(value, Decimal) else value for field, value in group.items()}
                              for key, group in sorted(currencies.items())}, 'rejected_rows': len(rejected), 'duplicate_rows': duplicates}
    output = Path(output).absolute()
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise ValueError('output must be a directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.reconcile-', dir=output.parent))
    previous = None
    try:
        for filename, fields, rows in [('reconciliation.csv', ['invoice_id','currency','invoiced','paid','balance','status'], lines),
                                       ('rejected.csv', ['source','row','reason'], rejected)]:
            with (stage/filename).open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        (stage/'summary.json').write_text(json.dumps(summary, sort_keys=True) + '\n')
        if output.exists():
            previous = Path(tempfile.mkdtemp(prefix='.previous-', dir=output.parent))
            previous.rmdir()
            os.replace(output, previous)
        try:
            os.replace(stage, output)
        except BaseException:
            if previous is not None:
                os.replace(previous, output)
                previous = None
            raise
        if previous is not None:
            shutil.rmtree(previous)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return summary


def main():
    parser = argparse.ArgumentParser()
    for name in ('invoices', 'payments', 'output'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(reconcile(args.invoices, args.payments, args.output), sort_keys=True))
        return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
