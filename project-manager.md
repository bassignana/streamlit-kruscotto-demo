# 1. Snippets
Run the following code snippets to 'automate' running the project.
In pycharm there is a bug in running fragments.

Initialized with: 
uv init --python 3.13

```bash
# Before running any snippet,
# ensure that the pwd is correct.
pwd
```

Add packages with versioning:
```bash
uv add 'streamlit==1.47.0'
uv add 'pandas==2.3.0'
uv add 'supabase==2.16'
uv add 'plotly==6.2'

```
uv add 'streamlit-aggrid==1.1.7'

Manage local development inside the venv
```bash
source .venv/bin/activate
which python3
python3 --version
```

Deploy procedure
```bash
# 1. Update the requirements. The changes will be picked up by the
#    Streamlit community Cloud. 
uv export --format requirements-txt --output-file requirements.txt

# 2. Commit the changes.
```

For the list of COMMON and UNCOMMON tags between all invoices:
python3 invoice_common_tags.py fatture_emesse/ fatture_ricevute 

Seeding the database
python3 tool_reset_db.py --noseed

# 2. DB
Here I prefer a managed supabase account in order to avoid to 
manage the local supabase instance for now.

For a temporary development environment, I've created a new 
Supabase project and I manually switch the credentials in the 
secrets.toml file.

# Meeting Notes
## Ven 1 Agosto 2025
- gestione delle scadenze non inserite (come casse e anagrafiche)
- come gestire il pagamento delle rate rispetto alle visualizzazioni? 4 righe?
- 
- importazione: importazione in base anagrafica unica.
- possibilita' di impostare il saldo iniziale ogni mese.
- >>> data pagamento di default: data documento + 1
- cassa: Iban o da definire
- fatture a 12 mesi, flusso di cassa da oggi in avanti
- visualizzare flussi per data, banca, cliente
- default non incassata

- accessi seprarati, dati separati
- iva, contributi, ..., nella dashboard
- altri movimenti anche positivi, come ordini
- Visione: saro' in grado di pagare?

# Features - Design
data -> filter() => op() with views!

Design decision: It would be more natural on a db perspective to treat every 
term due date the same: if an invoice has 0,1 or more terms, they all get 
inserted in the rate_fatture_* tables.
BUT for now I want to keep them separate. If the invoice has only one term, 
then the term will be set in the fatture_* table, if the invoice has multiple terms,
then they will be set in the rate_fatture_* table. This is a weird distinction,
but I want to code more of the front end to understand all the tradeoffs



UPLOADER
- get info on anagrafica cliente / profilo
- one single uploader for emesse / ricevute
user_data or {}
what is a session? Is it saved in local memory and then used for re-auth without login form.
  "options": {
  "email_redirect_to": "https://example.com/welcome",
  },
@st.cache




FLUSSI DI CASSA
Forward looking.
|30|60|||||||||||||
tabella_saldo_iniziale
- display saldo iniziale
- ? quick add saldo iniziale
tabella_incassi_group_by_casse
tabella_pagamenti_group_by_casse
tabella_saldo_finale
graph_incassi_group_by_casse
graph_pagamenti_group_by_casse




?
[] Visualizzatore scadenze divise per mese (ed eventuale rimando 
   alla relativa fattura) nella dashboard principale.
[] Gestione dei pagamenti delle rate piu' veloci, magari con una data
   table. Soprattutto in vista della gestione di molte scadenze.
[] Aggiunta di un campo per permettere all'imprenditore di riconoscere 
   al volo le fatture.
[] Dashboard data range: select with slider.
[] # todo: In what part of the application do I need to ensure datatypes consistency?
   What I might do, for READ query at least, is that I create a function that will
   read the config or some other info and convert any data that I might have in the 
   correct data format. Then I do all queries either in a separate file, or I use
   this function to tranform the result.data that I get from the py API.
   Maybe leaving the query where they are is better, also because I can do 
   herror handling on the result right there.
[] Associa fattura altre spese: preventivo vs consuntivo
[] classic streamlit groupby option for interacting with fatture and flussi di cassa



1.0

USER
[] Nelle pagine di add, modify ... mostrare solo le fatture che possono essere effettivamente
modificate, cosi' posso rimandare alle pagine con un bottone eventualmente.
[] 2 Graphs
[] Cassa e anagrafica per Fatture Emesse, ma ha senso visualizzare? Perche' ci
   saranno dei casi dove non ho tutte le info, quindi come nella dashboard dovrei
   individuare tutte le fatture che hanno dati mancanti. Qui si tratterebbe di diventare
   un visualizzatore di fatture... out of scope.


DEV
[] Test scadenze 1$ per day.
[] Divisione dei payment terms in due tabelle.
[] RLS

# 3. Project automation
Goal: starting from the initial sql tables definition and 
a config file detailing what variables in the sql are corresponding
to the values inside the xml tag, I want to create automatically:
- upload page with custom xml extractor to db
- add, modify, delete forms with db api
- visualization?
- tests?

## Python approach
DEPRECATED: If I use the supabase auth API, the test users profiles
are persisted even If I delete everything in the public db.
So I have one BIG sql file that I copy and paste into the sql editor
of supabase to reset the db.

NOTE: since I cannot run raw sql directly in supabase from
the python API, I use the following workaround where I have
to create the following procedure manually once.
```sql
   -- Run this ONCE in Supabase SQL Editor
   -- Allows Python script to execute any SQL
   CREATE OR REPLACE FUNCTION exec_sql(sql_query TEXT)
   RETURNS TEXT AS $$
   BEGIN
       EXECUTE sql_query;
       RETURN 'OK';
   EXCEPTION
       WHEN OTHERS THEN
           RETURN 'ERROR: ' || SQLERRM;
   END;
   $$ LANGUAGE plpgsql SECURITY DEFINER;
```

then, for resetting the database, I can use:
`python reset_db.py`
or to reset the database without test data: 
`python reset_db.py --noseed`

For now, the only test user and credentials are stored 
in the secrets.toml so that I can commit the seeding script.

## Supabase + sql file approach
See above deprecation notice.

## TODOS
[] Ask in chat Invoice Persistene in Supabase:
[] add soft delete, maybe with a function or tirgger or transaction 
[] How to test and benchmark concurrency and not-locking claims (generate scirpt from CREATE)

[] create a basic auth template for streamlit for automatic auth 
   (Supa auth chat), that works for registering users without 
   confirmation email, but with pwd recovery already setup 
   (streamlit-app-authnotworkding) for an example.

[] get create and rules for auth tables

IF IT IS REALLY EASIER, THEN IT SHOULD FEEL EASIER!
- no weird imports or structure.
- config base rendering of pieces of UI. No component. simple switch and code.
- pass db client in session state.
- Put everything in different pages. copy paste.
- no page generator.

for later:
- auto gen cypress tests
- auto gen test data
- redux pattern for state management, maybe I can put state for each component in a dictionary with the name
  of the component inside the global session state

NOTE FOR FUTURE DEV:
MAYBE, there is un unspoken assumption in the way that I've coded so far:
there cannot be a column in a database that it is not present in the XML_FIELD_MAPPING?
If I use the xml_mapping to check things, then I incour the risk of leaving columns out.
This is bad.





















































## Adding a new table flow
In sql file: 
- add delete statement
- add table definition
- enable and add RLS
- add any separate unique constraint
- add triggers

Test sql file

