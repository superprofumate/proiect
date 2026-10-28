from unittest.mock import Mock
import sqlite3
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.models import Client, Rules
from app.engine import evaluate
from app.bedrock import BedrockExplainer
from app.audit import Audit
from app.main import app, repository

RULES = Rules(version='test', high_risk_threshold=.7, low_relationship_max=1)

def customer(**changes):
    return Client.model_validate(dict(client_id=1, nivel_relatie=1, scor_risc=.2,
                                     flag_frauda_interna=False, flag_pep=False) | changes)

@pytest.mark.parametrize('changes,action', [({}, 'relationship_check_in'),
    ({'nivel_relatie': 3}, 'standard_follow_up'),
    ({'scor_risc': .7}, 'manual_review'),
    ({'flag_pep': True}, 'manual_review'),
    ({'flag_frauda_interna': True}, 'manual_review')])
def test_rules(changes, action):
    assert evaluate(customer(**changes), RULES).action == action

@pytest.mark.parametrize('risk', [-1, 2, float('nan')])
def test_invalid_risk(risk):
    with pytest.raises(ValidationError):
        customer(scor_risc=risk)

def test_tool_loop():
    client = Mock()
    client.converse.side_effect = [
        {'stopReason': 'tool_use', 'output': {'message': {'role': 'assistant', 'content': [
            {'toolUse': {'name': 'get_retention_decision', 'toolUseId': 't1', 'input': {}}}]}}},
        {'stopReason': 'end_turn', 'output': {'message': {'role': 'assistant', 'content': [{'text': 'Explicație'}]}}}]
    assert BedrockExplainer(client, 'test').explain(evaluate(customer(), RULES)) == 'Explicație'
    payload = client.converse.call_args.kwargs['messages'][2]['content'][0]['toolResult']['content'][0]['json']
    assert 'client_id' not in payload
    assert payload['action'] == 'relationship_check_in'

def test_no_tool_rejected():
    client = Mock()
    client.converse.return_value = {'stopReason': 'end_turn', 'output': {'message': {
        'role': 'assistant', 'content': [{'text': 'Invented'}]}}}
    with pytest.raises(ValueError):
        BedrockExplainer(client, 'test').explain(evaluate(customer(), RULES))

def test_audit(tmp_path):
    path = tmp_path / 'audit.db'
    Audit(path).record('id', 'success', evaluate(customer(), RULES))
    with sqlite3.connect(path) as db:
        assert db.execute('select status from audit').fetchone()[0] == 'success'

def test_api(monkeypatch, tmp_path):
    import app.main as main
    monkeypatch.setattr(main, 'Audit', lambda _: Audit(tmp_path / 'audit.db'))
    monkeypatch.setenv('APP_API_KEY', 'test-token')
    repo = Mock()
    repo.get_client.return_value = customer()
    app.dependency_overrides[repository] = lambda: repo
    try:
        with TestClient(app) as client:
            assert client.get('/health').status_code == 200
            assert client.post('/retention/evaluate', json={'client_id': 1}).status_code == 401
            headers = {'x-api-key': 'test-token'}
            result = client.post('/retention/evaluate', headers=headers, json={'client_id': 1})
            assert result.status_code == 200
            assert result.json()['explanation'] is None
            assert client.post('/retention/evaluate', headers=headers, json={'client_id': -1}).status_code == 422
            repo.get_client.side_effect = LookupError()
            assert client.post('/retention/evaluate', headers=headers, json={'client_id': 8}).status_code == 404
    finally:
        app.dependency_overrides.clear()

@pytest.mark.parametrize('name,args', [('sql', {}), ('get_retention_decision', {'client_id': 9})])
def test_tool_scope(name, args):
    client = Mock()
    client.converse.return_value = {'stopReason': 'tool_use', 'output': {'message': {
        'role': 'assistant', 'content': [{'toolUse': {'name': name, 'toolUseId': 't', 'input': args}}]}}}
    with pytest.raises(ValueError):
        BedrockExplainer(client, 'test').explain(evaluate(customer(), RULES))

def test_tool_limit():
    client = Mock()
    client.converse.return_value = {'stopReason': 'tool_use', 'output': {'message': {
        'role': 'assistant', 'content': [{'toolUse': {
            'name': 'get_retention_decision', 'toolUseId': 't', 'input': {}}}]}}}
    with pytest.raises(ValueError, match='limit'):
        BedrockExplainer(client, 'test').explain(evaluate(customer(), RULES))
    assert client.converse.call_count == 4

def test_repository_projection():
    from app.repository import SupabaseRepository
    db = Mock()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [customer().model_dump()]
    assert SupabaseRepository(db).get_client(1).client_id == 1
    db.table.assert_called_once_with('clients')
    db.table.return_value.select.return_value.eq.assert_called_once_with('client_id', 1)
