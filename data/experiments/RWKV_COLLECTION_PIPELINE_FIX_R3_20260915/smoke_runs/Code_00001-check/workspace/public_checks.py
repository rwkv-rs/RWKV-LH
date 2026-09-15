import json,subprocess,sys
stdin,expected=('3 2\n2 2\n2 2\n', '12\n')
r=subprocess.run([sys.executable,'solution.py'],input=stdin,text=True,capture_output=True,timeout=10)
passed=r.returncode==0 and r.stdout.rstrip()==expected.rstrip()
print(json.dumps({'checks':[{'case':1,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'passed':passed}],'passed':passed},ensure_ascii=False))
sys.exit(0 if passed else 1)
