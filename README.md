# NEXXT AI — backend de retenție

Prototip Python pentru Baza2 (`mszfkbstlxpveokykshr`). Accesul aplicației este separat de conexiunea Supabase din chat: completează cheia backend local. `.env` existent nu a fost modificat.

## Pornire în terminalul VS Code

```bash
cd /Users/andre/Documents/Andrew/NEXXT-AI/proiect
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

La prima instalare, dacă `.venv` lipsește: `python3 -m venv .venv`.

Completează manual `.env`, folosind `.env.example` ca referință; nu copia exemplul peste fișierul existent:

- `AWS_BEARER_TOKEN_BEDROCK`: cheia Bedrock introdusă de tine; boto3 o citește din mediu.
- `AWS_REGION`: regiunea în care modelul este disponibil.
- `BEDROCK_MODEL_ID`: ID exact de model Claude Haiku 4.5 sau inference profile din consola AWS. Un nume prescurtat poate să nu funcționeze.
- `SUPABASE_URL=https://mszfkbstlxpveokykshr.supabase.co`
- `SUPABASE_KEY`: cheia secret/service_role a Baza2, exclusiv pe backend. Nu dezactiva RLS. Cheia publishable singură poate să nu aibă acces la clienți.
- `APP_API_KEY`: un token lung ales de tine pentru acest API local.

Deschide http://127.0.0.1:8000/docs și folosește `POST /retention/evaluate`. Introdu tokenul local în câmpul `x-api-key`, apoi corpul:

```json
{"client_id": 1, "explain": false}
```

`explain: false` testează Supabase și regulile fără apel AWS. `explain: true` adaugă explicația Claude, cu cost de utilizare Bedrock. Repornește serverul după editarea `.env`. `/health` confirmă doar serverul local, nu conexiunile externe.

## Ce este implementat

- Validare Pydantic pentru cereri, date și reguli.
- Citire limitată din `clients`, fără nume sau etichetele viitoare din `ml_labels`.
- Motor determinist: prioritate verificării umane pentru flaguri/risc, apoi nivelul relației.
- Converse boto3 cu tool calling, instrument permis explicit, argumente validate, maximum 4 apeluri; explicația nu înlocuiește decizia.
- Audit SQLite local în `var/audit.sqlite3`, fără chei, prompturi sau mesaje brute de eroare.
- API protejat prin token local, erori externe mascate; fără operațiuni de scriere în Supabase.

Regulile din `config/retention.yaml` sunt **demonstrative**, nu o politică bancară validată. Nu calculează un scor de churn; folosesc scorul existent și nivelul relației. Explicația LLM necesită verificare umană. Integrarea celorlalte tabele și ofertele concrete se adaugă când definițiile și regulile finale sunt disponibile. API-ul este pentru un operator local; autentificarea pe utilizatori, autorizarea pe clienți și auditul centralizat sunt necesare înainte de publicare.

## Teste

```bash
python -m pytest -q
```

Testele folosesc date simulate și nu apelează AWS/Supabase. Verificarea reală necesită cheile tale. Documentație de integrare: [AWS Converse](https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-runtime/client/converse.html), [Supabase Python](https://supabase.com/docs/reference/python/select).
