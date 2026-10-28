from pathlib import Path
import yaml
from .models import Client, Decision, Rules

ROOT = Path(__file__).resolve().parents[1]

def load_rules():
    return Rules.model_validate(yaml.safe_load((ROOT / 'config/retention.yaml').read_text()))

def evaluate(client: Client, rules: Rules) -> Decision:
    reasons = []
    if client.flag_frauda_interna:
        reasons.append('internal_fraud_flag')
    if client.flag_pep:
        reasons.append('pep_review')
    if client.scor_risc >= rules.high_risk_threshold:
        reasons.append('risk_threshold')
    if reasons:
        action = 'manual_review'
    elif client.nivel_relatie <= rules.low_relationship_max:
        action, reasons = 'relationship_check_in', ['low_relationship_level']
    else:
        action, reasons = 'standard_follow_up', ['standard_relationship']
    return Decision(client_id=client.client_id, rules_version=rules.version,
                    action=action, reasons=reasons)
