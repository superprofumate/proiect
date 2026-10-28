from pydantic import BaseModel, ConfigDict

class ToolInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

class BedrockExplainer:
    def __init__(self, client, model_id):
        self.client, self.model_id = client, model_id

    def explain(self, decision):
        # Tool is scoped to the already evaluated client. No SQL or arbitrary IDs.
        payload = decision.model_dump(exclude={'client_id'})
        messages = [{'role': 'user', 'content': [{'text':
            'Consultă get_retention_decision și explică în română recomandarea demonstrativă.'}]}]
        tool = {'toolSpec': {'name': 'get_retention_decision',
                'description': 'Returnează decizia deterministă pentru cazul curent.',
                'inputSchema': {'json': ToolInput.model_json_schema()}}}
        used_tool = False
        for _ in range(4):
            response = self.client.converse(
                modelId=self.model_id,
                system=[{'text': 'Folosește instrumentul înainte de răspuns. Explică doar decizia primită. '
                         'Nu inventa oferte, sume, aprobări sau promisiuni. Este necesară verificare umană.'}],
                messages=messages, toolConfig={'tools': [tool]},
                inferenceConfig={'maxTokens': 600, 'temperature': 0})
            message = response['output']['message']
            messages.append(message)
            if response['stopReason'] == 'tool_use':
                results = []
                for block in message['content']:
                    if 'toolUse' not in block:
                        continue
                    call = block['toolUse']
                    if call['name'] != 'get_retention_decision':
                        raise ValueError('Unsupported tool')
                    ToolInput.model_validate(call['input'])
                    used_tool = True
                    results.append({'toolResult': {'toolUseId': call['toolUseId'],
                                    'content': [{'json': payload}]}})
                if not results:
                    raise ValueError('Missing tool call')
                messages.append({'role': 'user', 'content': results})
            elif response['stopReason'] == 'end_turn' and used_tool:
                text = '\n'.join(b['text'] for b in message['content'] if 'text' in b).strip()
                if text:
                    return text
                raise ValueError('Empty explanation')
            else:
                raise ValueError('Incomplete or ungrounded response')
        raise ValueError('Tool round limit exceeded')
