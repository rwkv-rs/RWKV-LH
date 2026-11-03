"""Conservative duplicate gates for independently authored project candidates."""
import io
import keyword
import re
import tokenize
from pathlib import PurePosixPath

from ..contamination import tokens, shingles

VERSION='original-project-diversity.v1'
JS_WORDS=set('if else for while do return throw try catch finally const let var function class extends new async await import export from default switch case break continue typeof instanceof in of true false null undefined this super'.split())
JS_TOKEN=re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`|[A-Za-z_$][\w$]*|\d+(?:\.\d+)?|\S',re.S)


def code_shingles(files):
    grams=set()
    for name,content in files.items():
        suffix=PurePosixPath(name).suffix
        if suffix not in ('.py','.js','.mjs','.cjs'):continue
        stream=[]
        if suffix=='.py':
            try:
                for token in tokenize.generate_tokens(io.StringIO(content).readline):
                    kind,text=token.type,token.string
                    if kind in (tokenize.COMMENT,tokenize.NL,tokenize.NEWLINE,tokenize.ENDMARKER):continue
                    if kind==tokenize.NAME:stream.append(text if keyword.iskeyword(text) else 'ID')
                    elif kind in (tokenize.NUMBER,tokenize.STRING):stream.append('VALUE')
                    elif kind in (tokenize.INDENT,tokenize.DEDENT):stream.append(str(kind))
                    else:stream.append(text)
            except (tokenize.TokenError,IndentationError):
                raise ValueError('invalid Python source during structural diversity audit: '+name)
        else:
            for text in JS_TOKEN.findall(content):
                if text.startswith(('//','/*')):continue
                if text[0] in '\"\'`' or text[0].isdigit():stream.append('VALUE')
                elif re.match(r'[A-Za-z_$]',text):stream.append(text if text in JS_WORDS else 'ID')
                else:stream.append(text)
        grams.update(shingles(stream,13))
    return grams


def audit(task, prior):
    request=shingles(tokens(task['request']),5)
    structure=code_shingles(task['reference_files'])
    matches=[]
    for other in prior:
        other_request=shingles(tokens(other['request']),5)
        other_structure=code_shingles(other['reference_files'])
        text_score=len(request&other_request)/len(request|other_request) if request or other_request else 1
        code_score=len(structure&other_structure)/len(structure|other_structure) if structure or other_structure else 0
        if text_score>=.8 or code_score>=.85:
            matches.append({'id':other['id'],'request_jaccard':text_score,'normalized_code_jaccard':code_score})
    return {'version':VERSION,'passed':not matches,'matches':matches,
        'thresholds':{'request_5gram_jaccard':.8,'normalized_code_13gram_jaccard':.85},
        'compared_projects':len(prior),'normalized_code_shingles':len(structure)}
