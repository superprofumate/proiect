import os
import secrets
from uuid import uuid4
import boto3
from botocore.config import Config
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from supabase import create_client
from .audit import Audit
from .bedrock import BedrockExplainer
from .engine import ROOT, evaluate, load_rules
from .models import Request, Response
from .repository import SupabaseRepository

load_dotenv(ROOT / '.env', override=False)
app = FastAPI(title='NEXXT AI — retention prototype')

def authorize(x_api_key: str = Header(default='')):
    expected = os.getenv('APP_API_KEY', '')
    if not expected:
        raise HTTPException(503, 'Configurează APP_API_KEY în .env')
    if not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(401, 'Token invalid')

def repository():
    url = os.getenv('SUPABASE_URL', 'https://mszfkbstlxpveokykshr.supabase.co')
    key = os.getenv('SUPABASE_KEY')
    if not key:
        raise HTTPException(503, 'Configurează SUPABASE_KEY în .env')
    return SupabaseRepository(create_client(url, key))

def explainer():
    model = os.getenv('BEDROCK_MODEL_ID')
    if not model:
        raise HTTPException(503, 'Configurează BEDROCK_MODEL_ID în .env')
    client = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'eu-central-1'),
                          config=Config(connect_timeout=5, read_timeout=45,
                                        retries={'max_attempts': 2, 'mode': 'standard'}))
    return BedrockExplainer(client, model)

@app.get('/health')
def health():
    return {'status': 'ok', 'mode': 'prototype'}

@app.post('/retention/evaluate', response_model=Response, dependencies=[Depends(authorize)])
def retention(body: Request, repo=Depends(repository)):
    request_id = str(uuid4())
    audit = Audit(ROOT / 'var/audit.sqlite3')
    decision = None
    try:
        decision = evaluate(repo.get_client(body.client_id), load_rules())
        explanation = explainer().explain(decision) if body.explain else None
        audit.record(request_id, 'success', decision)
        return Response(request_id=request_id, decision=decision, explanation=explanation)
    except LookupError:
        audit.record(request_id, 'not_found')
        raise HTTPException(404, 'Client inexistent sau inaccesibil') from None
    except HTTPException:
        audit.record(request_id, 'configuration_error', decision)
        raise
    except Exception:
        audit.record(request_id, 'failed', decision)
        raise HTTPException(502, {'message': 'Evaluarea nu a putut fi finalizată',
                                  'request_id': request_id}) from None
