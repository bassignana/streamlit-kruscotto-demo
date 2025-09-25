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
uv add 'pytest==8.4.2'
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
NOTE: Now that I add packages that I don't need for the deployment, like
pytest and cypress, how do I create the requirement file for production?
Maybe the easiest thing is to not make this distinction to have both envs
equal, or I can create a dummy prod env and do the above with that.

For the list of COMMON and UNCOMMON tags between all invoices:
python3 invoice_common_tags.py fatture_emesse/ fatture_ricevute 

OLD
Seeding the database
python3 tool_reset_db.py --noseed

Lunch db tests
Create .pgpass and give right permissions with `chmod 0660 .pgpass` like mentioned
in Postgres docs.
Install pgprove. TODO: link to the page with instructions.
```bash
source .secrets/.env.sh

pg_prove -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --ext .sql -r "$PGTAP_TEST_PATH"
pg_prove -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --ext .sql -r "$PGTAP_TEST_PATH"/specific_test_file.sql
```

Cypress testing: 
installation procedure detailed in the ObsVault folder.
run with:
```bash
cd e2e-tests
source ../.secrets/.env.sh

npx cypress open
```


# 2. DB
Here I prefer a managed supabase account in order to avoid to 
manage the local supabase instance for now.

Remember to set the correct timezone.
It will influence automatically inserted data!
```sql
alter database postgres
set timezone to 'Europe/Rome';
```

## Complex casse logic


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

## Mar 26 Agosto 2025
CASSE:
- Nelle fatture ricevute, la cassa che vado ad indicare quando imposto
  le scadenze di pagamento saranno le MIE, non quelle del fornitore?
- Nel tab delle casse posso fare un crud completo sulle casse che imposto
  io manualmente, ma se un iban e' stato letto da fattura, potrei in teoria,
  solo modificarne il nome, ma anche qui ci sarebbe un po' di lavoro da fare,
  perche' nella fattura ci sarebbe un nome diverso.
- Queste operazioni sulle casse le potrei fare solo perche' userei l'iban come
  id unico per identificare una cassa
ANAGRAFICHE:
- Stesso discorso sopra per le anagrafiche, ma con una domanda: dove le uso le 
  anagrafiche in questo momento? Sono essenziali?
- Possiamo comunque conservare le informazioni dei clienti dalle fatture emesse,
  in modo da poter fare, ad esempio, una classifica dei clienti che mi devono 
  di piu' come nell'attuale dashboard, ma comunque senza dare la possibilita' 
  di modificare o aggiungere anagrafiche, al piu' leggerle, ma non saprei a che pro.
ALTRI MOVIMENTI:
- in una primissima fase, nessuna connessione con le fatture. si carica la fattura 
  e si elimina il movimento.
FLUSSI DI CASSA
- come fare l'impostazione del saldo iniziale? magari solo al primo mese?
  potrei fare un riquadro dove per ogni cassa imputo di default il flusso
  di cassa del mese precedente, ma modificabile in modo da poter sovrascrivere
  il saldo iniziale. Al termine del mese, i valori verranno riaggiornati, anche
  se erano stati valorizzati manualmente. Mettere un avviso magari.
- a 60 gg vuol dire solo il secondo mese, non cumulativo corretto?

Casse:
Iban | nome | descrizione
posso aggiungere cassa, anche senza iban (contanti)
Nei campi che leggo da fattura posso solo modificare la descrizione.
Nei campi che aggiungo io posso modificare tutto?
Faro' sempre una query da questa tabella, che risultera' in una sola colonna:
coalesce(descrizione, nome, iban), che utilizzero' nei menu' a scelta multipla e 
nelle altre visualizzazioni.
Nelle fatture ricevute mi devo assicurare di utilizzare le mie casse!

A tendere:
Anagrafiche aziende: leggere CF e PIVA e aggiornare con l'ultimo nome disponibile
Mantenere storico scadenza originaria nel database, lato statistiche.
filtro altri movimenti x tipo nel sommario
movimenti passivi categoria iVA ALERT

Flussi di cassa:
flussi di cassa come mvp DAL MESE CORRENTE, parte bloccata scaduti,
e saldi iniziali selezionabili nell'anagrafica azienda con avviso ogni primo
del mese se cambiarli o lasciarli uguali.
numeri allineati a dx, tutte le cose allineate a dx.
eliminare opzioni di visualizzazione / sort nelle tabelle.
no euro 6.000,cents
stesse dimensioni delle colonne tra le varie tabelle
Intestazione colonne centrate

varie:
TEMPLATES
alert utente iscritto
altri movimenti: menu a tendina blindata

Beta:
BRAKING:
[] IDEA: can I use st.html() to always show the scrollbar in the df that I know that will be large?
[x] quando creo un movimento, modifico dalla tabella un valore e poi clicco quando sono
   ancora nella tabella sul puslante salva, NON SALVA, ma devo cliccare una seconda 
   volta! Sembra che il primo click faccia uscire la persona dalla tabella in modifica, 
   mentre il secondo faccia effettivamente effetto sul salva.
   Dovrebbe accadere anche con ANNULLA ma il pulsane annulla NON FUZIONA! Funziona solo se
   clicco da qualche parte che non sia il pulsante annulla stesso.
   Questa cosa accade solo con i bottoni e per una questione di tempistiche e rerun:
   probabilmente quando esco dalla modifica di una cella cliccando con il mouse, 
   c'e' una specie di rerun o comunque un caricamento, che si vede in alto a dx.
   se invece clicco sul pulsante salva, ma aspetto che quel caricamento finisca prima di 
   rilasciare, il pulsante funziona correttamente. Magari e' anche un problema il fatto che
   la funzione che uso nel pulsante prenda in input il valore di ritorno del dataframe 
   modificato: magari mettendo quel valore nello stato la situazione si risolve.
   NON risolto mettendo il df in un  st.fragment()
   OPEN ISSUE: https://github.com/streamlit/streamlit/issues/7868
   Patched: dropdown menu to include save button.
[] place where clause in all views
[x] When I delete movement, I need to delete relative terms also! Both in db and in transaction
[] The above with all CRUD OPS in all things
[x] I need to upsert terms when I change date or number of a movement, also for invoices
[] ?? nelle rate ho 3 date, la data del pagamento, la presunta scadenza e la data di pagamento effettiva:
   devo impedire, nella visualizzazione dei termini, di modificare la data documento ed il numero: la chiave.
   per ora potrei mettere il solito avviso o non rendere modificabili le colonne! Also for casse!
[] remove all time.sleep with spinners and for sure don't give the success message early
   otherwise if the user will click outside of the page while the operation is still 
   pending, the op will be canceled!!
[x] Casse modify does not work
[] In the annulla button I have to implement the refetch: it is easier to implement and right now
   the state management is broken, so that when I save and fail a control and click annulla, the 
   broken state will be used.
[x] In the uploader I have to insert a rerun if I want to update the tables, but doing so will make almost
   impossible to read the summaries and warnings
[x] Screen: in fatture analisi, if there are no attivi o passivi, there is a floating point errors.
[] Test everyware that when there is few data, the app behaves correctly
[] Movimenti > when creating terms with rapid config, then changing the edited df removing one of the 
   amounts, then click auto division, the df is not updated!
   I think that this I cannot fix since it probably is a problem with the internal state of the streamlit component.
[x] Same thing above when update the fattura attesa!
[x] When I add a new entry in the altri movimenti df, I get the old selection index data in the terms df
[x] Fix the two above bugs in fatture page
[] When there are no active or passive things, in the flussi di cassa I have an error and an ugly situation.
   I have to check the whole app and see what happens when there are no data or just active stuff or just passive 
   stuff
[x] Check that in movimenti, when I add a movement, then i modify its import, the term is not updated 
   and there is no warning that I have a discrepancy!
[] Fatture ricevute > modify > i cannot modify the PIVA of fornitore!
[x] Check I have "scadenze incongruenti" but no alert is appearing under the summary.
[] There are a couple of manual things: 
   - the month in cashflow is not dynamic
   - this (movimenti e fatture): different_year_attivi = supabase_client.table('fatture_emesse').select('*') \
    .or_('fe_data_documento.lt.2025-01-01,fe_data_documento.gt.2025-12-31').execute()
      different_year_passivi = supabase_client.table('fatture_ricevute').select('*') \
    .or_('fr_data_documento.lt.2025-01-01,fr_data_documento.gt.2025-12-31').execute()
[x] Screen: When I divide automatically the malformed example terms, I get an error in floating point 
   conversion.
[] I should check floating to money conversion everywhere
[] Uploader: sometimes (the first time) the button 'carica fatture' appears. The following times the upload starts
   immediately
[] I've modified the malformed invoice, deleted it, then reaploaded it, the old terms are still in the session state
   hopefully not in the db

[] Pagina IVA: get data and analysis with soglia

[] RIUNIONE: visuallizzazione tab caricamento xml: tab, expander, cosi' : tab upload fatture
[]           metric sx grafico: cambiare titoli e metric
[]           fattura con alert
[]           Toggle modifica dati e aggiornamento situazione
[]           Nelle fatture ci sono campi che posso modificare ma non sono letti da nessuna parte
[]           DNS
[]           verifica button
Riunione 5 settembre:
- reminder altri movimenti per cancellazione attesa fattura
[x] movimenti: cliente dropdown(IMPOSSIBILE), passivi: denominazione fornitore
- categorie tipologia movimenti:  stipendi netti, contributi previdenziali, ...
- analisi > analisi IMPOSTE: 
- alert IVA: soglia statica 
[x] Colonna anomalie o riga in rosso
- CSV per caricare automaticamente tanti movimenti
[x] font grande (IMPOSSIBILE), colonna sx, font grassetto intestazione (IMPOSSIBILE)
[x] fatture / movimenti: correggere totali, fatture 'ad oggi' rimuovere. sost: saldo
[x] SOLO FATTURE E MOVIMENTI DEL 2025, avviso per sommario


flussi di cassa
[] Ask: mettere colonna totali a sx?
[] Mettere ...string if cassa is too long, with tooltip that will tell to go change name?
[x] cambiare colonna come da mail
[x] verificare che nei mesi ci stiano almeno -xxx.xxx,xx cifre
[x] chiedere nomi aggiornati per le colonne e verificarne gli ingombri, magari mettere 9 mesi?
[x] Adjust pixel column size.

[] columns in df visualization are not numeric and sort does not work correctly

[] I nomi devono essere strippati, magari direttamente in input al db?

all add and modify modal
[] keep data on save button
[] remove submit on enter
[] fix column ordering

[] nel profilo utente, compare prima l'avviso dell'anagrafica, senza poter fare un
   logout immediato
[] table headings in bold, maybe a markdown label in bold in column_configs
[] 'la fattura non contiente la piva al suo interno' aggiungere messaggio che dice dove andare a 
   trovare la schermata dove fare la modifica

1.0:
[] Number and date formatting, italian and same on input output
[] Scrollbar always present in tabular things
[] Quando modifico l'importo di un movimento, gli importi delle scadenze non vengono
   modificati! Aprire un menu di modifica o, comunque, impedire la prosecuzione.
Things to solve with regards to the database:
- [ ] always shown horizontal scrollbar
- [ ] left AND right fixed columns
- [ ] dropdown with suggestions or custom field
- [ ] selectable dataframe
- [ ] css to be streamlit like
- [ ] complex index
- [ ] font change
- [ ] testable
- [ ] be able to add or remove row 

Riunione 15 Settembre:
[x] centrare maschera login
[x] Errori gravi: Documenti da Verificare, chiusa, sotto
[x] aggiungere categoria ordini nei passivi
[x] Controllo sintassi CF: x lettere e x numeri. PIVA 11 numeri.
[] TEST, with appV1: Controllo sintassi CF: x lettere e x numeri. PIVA 11 numeri.
[x] Limite sulle fatture caricate 100 fatture acquisto / vendita in caricamento. ...(in questa varsione
   è possibile caricare fino a 50 fatture di acquisto e 50 di vendita)
[] Test max invoice upload limit
[x] sempre due centesimi nelle griglie delle tabelle
[] do I need to test for the above? maybe not, there are more urgent things 
[x] ordinameto fatture discendente data e mettere numero come chiave ordinaria
[] How do I test the above? with V1? only tested visually now
[x] check that the default time in the dataset is not behind by two hours 2025-09-16 08:33:07.588974 +00:00
[] Totale attivi dopo Agosto.
[] doppio indice nel dataframe mettendo: Da Incassare, dopo Scaduti.  Rimuovere 'Da incassare scaduti'
[] Come sopra: Da Pagere, 'da pagare scaduti'
[] Verificare calcolo del totale nelle query
[] Test sui totali? V1?


[x] flussi di cassa passivi, le casse devono essere LE MIE (accade in upload)  
[] fatture ritenute sono quelle che hanno le scadenze diverse
[] se nella fattura c'e la **condizione di pagamento MP 01** va direttamente nella cassa contanti e devo crearla se non esiste
[] mp 05 banca di default, tutto il resto non specificato
[] banca di default per le fatture emesse con colonna o menu spuntabile
[] mail supporto@kruscotto.it. La comunicazione di streamlit va nei log del db, mentre metto un messaggio per la mail.
[] Importo secco per il saldo iniziale nell'anagrafica azienda. Saldo Iniziale Mese Corrente.
   Aggiornato con il saldo finale del mese prima. Sempre modificabile.


RIUNIONE Lun 22 Settembre
[] <ImponibileImporto> È l'unico campo che ci interessa.
[] X Venerdi, cassa default in anagrafica azienda

PER RILASCIO:
[x] BUG: screen, probabilmente dovuta all'ordering della colonna, se seleziono una fattura, non vedo i termini
   corrispondenti.
[x] BUG: screen, duplicazione cassa quando creo una nuova cassa e poi la vado a selezionare in una fattura.
[?] BUG: screen, aggiungere manualmente una cassa prima di averne caricate altre da errore
[] PWD Dimenticata
[] Aumentare tempo sessione
[x] Analisi imposte: "Prossimo Rilascio"
[x] Contatti: mandare mail al supporto@kruscotto
[x] se non c'e la scadenza, DATA DOCUMENTO, sia per acquisti che vendite
[x] Togliere 2 mesi -> in oltre ASSICURANDOSI DI MANDARE TUTTI I TOTALI IN OLTRE DEI DUE MESI
[] Tile sx: aggiungere totali a dx df, Fatture ed altri mov.
[] TEST: i totali nelle varie pagine devono essere corretti, occhio ai BUG nelle casse
[x] Fatture mensili -> Fatturato (comprensivo di IVA)

RIUNIONE PRE RILASCIO

[] Anagrafica azienda BUG?
[] BUG Controllare casse
[] Flussi di cassa TOTALE BUG


[] Sommario altri movimenti non ci sono i decimali
[] Fatturato / Imposte al posto di Analisi Imposte
   All'interno mettere tab 
   Fatturato ... sarà operativa nei prossimi rilasci
[] Movimenti attivi / passivi nei flussi

Futuro
[] Aggiorna sbatte fuori
[] Pulsante di aggiunta cassa anche se non ci sono fatture





PATHS:
Documenti-movimenti-sommario
Documenti-movimenti-movimenti attivi
state: empty
    op(add) -> !required
state: all ops available



## Successiva:
- Nella gestione scadenze, per ora avviso discrepanza tra impostato e totale. 
  Differenza sempre presente occludeva un po' l'interfaccia.
- Potrebbe essere utile una finestra o un dropdown con un video gif delle operazioni 
  che si possono fare?
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
- add any separate unique constraint, WITH THE user_id IN IT!
- add triggers
Test sql file

For views:
- Use always WITH (security_invoker = true)
- always add WHERE user_id = auth.uid() in every query of the view
- be sure that RLS is enabled
- in the python api, omit .eq(user, 'user') since there is no user_id column
  in the view.

For generating CRUD elements:
Since I don't want to mess with the whole xml config needed to 
render elements correctly, for altri_movimenti I'll create a
separate config: altri_movimenti_config.py

IF some utils are taken from invoice_utils.py others from altri_movimenti_utils.py,
copy the util. Customization will be needed, now or in the future.




# Security
- In order for views to 'inherit' the RLS policies, I have to use the
  WITH (security_invoker = true) clause, but I don't know exactly how this works
  and it can be super dangerous. 
  The manual says: If any of the underlying base relations has row-level security enabled, 
  then by default, the row-level security policies of the view owner are applied, 
  and access to any additional relations referred to by those policies is determined 
  by the permissions of the view owner. 
  However, if the view has security_invoker set to true, 
  then the policies and permissions of the invoking user are used instead,
  as if the base relations had been referenced directly from the query using the view.
  But I don't really understand this and messing with roles will also possibly mess with 
  this. So, until I find time to sort this out, I'll specify both WITH (security_invoker = true)
  and WHERE clauses that will identify the authenticated user.
- 