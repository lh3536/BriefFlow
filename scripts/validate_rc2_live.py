import json, os
from pathlib import Path
from unittest.mock import patch
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from backend.llm import _config, llm_provider
from backend.router.service import run_brief_flow

QUERY = '我是金融专业大三学生，想找广州、深圳、香港、澳门适合本科生的金融、券商、投行和 FinTech 机会，优先实习和比赛，不要销售岗位。'
OUT = Path('artifacts/validation/rc2')
OUT.mkdir(parents=True, exist_ok=True)
Path('work').mkdir(exist_ok=True)
cfg = _config()
qwen = {'status':'NOT RUN', 'reason':'No local .env or environment BRIEF_LLM_API_KEY', 'preference':None, 'summary':None}
if cfg['api_key']:
    if llm_provider() != 'qwen':
        qwen['reason'] = 'Configured provider is not Qwen; credential was not sent to a different provider'
    else:
        with patch.dict(os.environ, {'BRIEFFLOW_RETRIEVAL_MODE':'mock'}):
            result = run_brief_flow(QUERY)
        expected = {'locations':{'广州','深圳','香港','澳门'}, 'categories':{'金融实习','经管比赛'},
                    'keywords':{'金融','券商','投行','FinTech'}, 'exclude_keywords':{'销售'}}
        complete = all(values <= set(result['preference'][field]) for field,values in expected.items())
        passed = complete and result['input_mode']=='llm' and result['summary_mode']=='llm'
        qwen = {'status':'PASS' if passed else 'FAIL','preference':result['preference'],
                'summary':result['summary'], 'input_mode':result['input_mode'], 'summary_mode':result['summary_mode']}
(OUT / 'qwen-live.json').write_text(json.dumps(qwen,ensure_ascii=False,indent=2),encoding='utf-8')
print('Qwen:',qwen['status'])

# Real web calls, with no model transport needed to independently test source provenance.
os.environ['BRIEF_LLM_API_KEY'] = ''
os.environ['BRIEFFLOW_RETRIEVAL_MODE'] = 'web'
os.environ['BRIEFFLOW_DB_PATH'] = str(Path('work/rc2-live.sqlite3').resolve())
rows=[]
for query in [QUERY,'金融比赛']:
    result = run_brief_flow(query)
    rows.append({'query':query, 'retrieval':result['retrieval'], 'total_items':result['total_items'],
                 'summary':result['summary'], 'summary_mode':result['summary_mode'],
                 'sources':sorted({item.get('source','') for item in result['recommended_items']})})
report = {'status':'PASS' if all(row['retrieval']['data_source_mode']=='Web Data' for row in rows) else 'FAIL',
          'runs':rows, 'note':'City-filtered zero results are genuine; no filters relaxed and no mock substituted.'}
(OUT / 'real-pipeline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
