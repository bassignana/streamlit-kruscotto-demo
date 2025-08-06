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

# Features
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

There is a functioning but not thoroughly tested version in 
Caricamente_xml_fatture_emesse.py, with config, xml extractor and
streamlit upload field all in one streamlit page.
What I want though is to create a separate xml reader that I can 
test with all the invoices, to be sure that I can read all fields.
Then, after I've tested it, I can use it with more certiantly.



[] Ask in chat Invoice Persistene in Supabase:
- add soft delete
- why the REF on user_id? to check? how checks works?
- ADD ALL rls to specify all clause in one statement CRUD
- various thing like type, CHECK, UNIQUE contraints etc...
- How to test and benchmark concurrency and not-locking claims (generate scirpt from CREATE)
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    numero_fattura VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('sale', 'purchase')),
    client_supplier VARCHAR(255) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    importo_totale_documento DECIMAL(15,2) NOT NULL,
    data_documento DATE NOT NULL,
    data_scadenza_pagamento DATE,
    xml_content TEXT, -- Store original XML
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Compound unique constraint
    UNIQUE(user_id, numero_fattura, type)
);

-- Essential indexes
CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_user_date ON invoices(user_id, data_documento);
CREATE INDEX IF NOT EXISTS idx_invoices_type ON invoices(user_id, type);

CREATE POLICY "Users can manage own data" ON your_table_name
    FOR ALL USING (auth.uid() = user_id);
```

[] create a basic auth template for streamlit for automatic auth 
   (Supa auth chat), that works for registering users without 
   confirmation email, but with pwd recovery already setup 
   (streamlit-app-authnotworkding) for an example.

[] get create and rules for auth tables

[] implement soft delete in both front and backend
``` python
def soft_delete_invoice(supabase: Client, invoice_id: str):
    """Soft delete an invoice"""
    try:
        result = supabase.table('invoices').update({
            'deleted_at': datetime.now().isoformat()
        }).eq('id', invoice_id).execute()
        
        return True, "Invoice deleted successfully"
    except Exception as e:
        return False, f"Error deleting invoice: {str(e)}"

def get_active_invoices(supabase: Client, user_id: str):
    """Get only non-deleted invoices"""
    return supabase.table('invoices')\
        .select('*')\
        .eq('user_id', user_id)\
        .is_('deleted_at', 'null')\
        .execute()

def restore_invoice(supabase: Client, invoice_id: str):
    """Restore a soft-deleted invoice"""
    return supabase.table('invoices').update({
        'deleted_at': None
    }).eq('id', invoice_id).execute()
```

[x] implement auto paging structure
creation so that in development
it is easy to put each single feature in a page. 
NOTE: do not call the folder 'pages',
that could be in conflict with the 
default streamlit behaviour.

[] remember that I can add material icons to pages 
st.Page("dashboard.py", title="Dashboard", icon=":material/search:")

[] Se avessi 2 tabelle, una per tutte le fatture
   emesse, e una per quelle ricevute. Eventualmente 4 tabelle se alle 2 aggiungo
   delle scadenze in altre tabelle.
   Poi creo un file di configurazione che associa,
   a ciascun campo nella tabella, un relativo tag xml. 
   Da li potrei autogenerare il processor xml,
   e i vari componenti streamlit per l'input e
   la visualizzazione.
   Ed eventuali test.


To do: IF IT IS REALLY EASIER, THEN IT SHOULD FEEL EASIER!
- no weird imports or structure.
- config base rendering of pieces of UI. No component. simple switch and code.
- pass db client in session state.
- Put everything in different pages. copy paste.
- no page generator.

?
- pass config into the state? 
- separate testing app?

for later:
- auto gen cypress tests
- redux pattern for state management, maybe I can put state for each component in a dictionary with the name
  of the component inside the global session state
- auto gen test data

