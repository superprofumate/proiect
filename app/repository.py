from .models import Client

class SupabaseRepository:
    def __init__(self, client):
        self.client = client

    def get_client(self, client_id: int) -> Client:
        # Explicit projection excludes names, financial details and future ML labels.
        result = (self.client.table('clients')
                  .select('client_id,nivel_relatie,scor_risc,flag_frauda_interna,flag_pep')
                  .eq('client_id', client_id).limit(1).execute())
        if not result.data:
            raise LookupError('Client not found')
        return Client.model_validate(result.data[0])
