"""Optional health-only smoke: python verify_public.py HOST PORT.

This intentionally does not certify booking/order behavior.
"""
import http.client
import json
import sys
connection = http.client.HTTPConnection(sys.argv[1], int(sys.argv[2]), timeout=5)
connection.request('GET', '/health')
response = connection.getresponse()
assert response.status == 200 and json.loads(response.read())['ok'] is True
connection.close()
print('health smoke passed; transactional behavior still requires tests')
