import time

import streamlit as st
from invoice_record_creation import extract_xml_records
from invoice_xml_processor import process_xml_list
from utils import setup_page
import streamlit.components.v1 as components

def update_key():
    st.session_state.uploader_key += 1

def toggle_is_processing_true():
    st.session_state.is_processing = True

def render_generic_xml_upload_section(supabase_client, user_id):

    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    partita_iva_result = supabase_client.table('user_data').select('ud_partita_iva').eq('user_id',user_id).execute()
    partita_iva_azienda = partita_iva_result.data[0].get('ud_partita_iva', None)

    response = supabase_client.table('fatture_emesse').select('id', count='exact').eq('user_id',user_id).execute()
    count_active = response.count
    response = supabase_client.table('fatture_ricevute').select('id', count='exact').eq('user_id',user_id).execute()
    count_passive = response.count

    if count_active + count_passive > 100:
        st.warning("Superato il limite massimo di 100 fatture. Contattare l'assistenza per ricevere più spazio.")
        return

    uploaded_files = st.file_uploader(
        "Carica fatture in formato XML. Attualmente è consentito caricare fino a 100 fatture.",
        type=['xml', 'p7m'],
        accept_multiple_files=True,
        # help="Carica fino a 20 fatture XML contemporaneamente",
        key=f"uploader_{st.session_state.uploader_key}"
    )
    st.html(
        """
        <style>
    
        [data-testid='stFileUploaderDropzoneInstructions'] > div > span {
        display: none;
        }
    
        [data-testid='stFileUploaderDropzoneInstructions'] > div::before {
        content: 'Trascinare qui le fatture';
        }
    
        [data-testid='stFileUploader'] [data-testid='stBaseButton-secondary'] { text-indent: -9999px; line-height: 0; } 
        
        [data-testid='stFileUploader'] [data-testid='stBaseButton-secondary']::after { line-height: initial; 
        content: "Seleziona"; text-indent: 0; }
    
        [data-testid='stFileUploaderDropzoneInstructions'] > div > small {
        display: none;
        }
        
        </style>
        """
    )

    # NOTE: with the key, the state is_processing is not working anymore as intended,
    # But for now it can be a goog solution!.

    if uploaded_files:

        if not st.session_state.is_processing:

            col1, space = st.columns([1, 3])

            with col1:
                st.info(f"{len(uploaded_files)} file pronti per il caricamento.")
                st.button("Carica Fatture", type="primary",
                           use_container_width=True, on_click=toggle_is_processing_true)

        # if Carica Fatture is pressed:
        if st.session_state.is_processing:
            with st.spinner("Elaborazione XML in corso..."):
                parsing_results, error = process_xml_list(uploaded_files)

                outs = []
                if parsing_results:
                    xml_records = extract_xml_records(parsing_results, partita_iva_azienda)

                    for xml in xml_records:

                        out = {
                            'filename': xml['filename'],
                            'data': xml['data'],
                            'status': xml['status'],
                            'error_message': xml['error_message'],
                            'record': xml['record'],
                            'terms': xml['terms'],
                            'invoice_type': xml['invoice_type'],
                            'inserted_record': {},
                            'inserted_terms': [],
                        }

                        try:
                            if out['status'] == 'error':
                                outs.append(out)
                                if 'non riguarda la partita IVA' in out['error_message']:
                                    st.warning(f"La fattura {out['filename']} non riporta la Partita IVA dell'azienda "
                                               f"al suo interno")
                                continue # to the next invoice record(s)

                            if out['invoice_type'] == 'emessa':
                                record_to_insert = out['record'].copy()

                                # The column user_id is also inserted inside the following postgres function.
                                # I leave this here in case we might change approach so that
                                # we don't forget to add the user id.
                                # NOTE; this is a dirty way of doing it, because this is NOT the
                                # record that will be inserted. That record is created in the
                                # RPC function.
                                #
                                # Todo: related to the "issue" of adding user_id both here and
                                # in the procedure, it has to be clear what implicit rules are
                                # respected inside the RPC function, for example if triggers for
                                # created_at and updated_at will function correctly, and if the
                                # automatic id setting with get_random_uuid() will work etc.
                                # The best thing should be that all RPC functions will work the same.
                                record_to_insert['user_id'] = user_id

                                # This is for the casse manage flow: the first time that I insert a record I have to
                                # assign a value to the display field.
                                for term in out['terms']:
                                    term['rfe_display_cassa'] = term.get('rfe_nome_cassa') or term.get('rfe_iban_cassa', None)

                                # st.write(out['terms'])

                                result = supabase_client.rpc('insert_record', {
                                    'table_name': 'fatture_emesse',
                                    'record_data': out['record'],
                                    'terms_table_name': 'rate_fatture_emesse',
                                    'terms_data': out['terms'],
                                    'test_user_id': user_id
                                }).execute()

                                if result.data and result.data.get('success'):
                                    out['inserted_record'] = record_to_insert
                                    outs.append(out)

                                else:
                                    if 'duplicate key value violates unique constraint' in result.data['error']:
                                        st.warning(f'La fattura {xml['filename']} è già presente nel database.')
                                    else:
                                        err_msg = f'Error during invoice INSERT for xml_record {result.data}'
                                        out['status'] = 'error'
                                        out['error_message'] = err_msg
                                        print(f'ERROR: {err_msg}')
                                        continue # to the next file

                            elif out['invoice_type'] == 'ricevuta':
                                record_to_insert = out['record'].copy()
                                record_to_insert['user_id'] = user_id

                                # This is for the casse manage flow: the first time that I insert a record I have to
                                # assign a value to the display field.
                                # NOTE: actually, I want to try to force None here, because in ricevute I should not
                                # get any cassa at the beginning.
                                for term in out['terms']:
                                    # term['rfr_display_cassa'] = term.get('rfr_nome_cassa') or term.get('rfr_iban_cassa', None)
                                    term['rfr_display_cassa'] = None

                                # st.write(out['terms'])

                                result = supabase_client.rpc('insert_record', {
                                    'table_name': 'fatture_ricevute',
                                    'record_data': out['record'],
                                    'terms_table_name': 'rate_fatture_ricevute',
                                    'terms_data': out['terms'],
                                    'test_user_id': user_id
                                }).execute()

                                if result.data and result.data.get('success'):
                                    out['inserted_record'] = record_to_insert
                                    outs.append(out)
                                else:
                                    out['status'] = 'error'
                                    out['error_message'] = f'Error during invoice INSERT for xml_record {out}'
                                    outs.append(out)
                                    continue # to the next file

                            else:
                                raise Exception(f"This branch should not be able to run, since "
                                                f"there should be an early return for invoice not emessa and "
                                                f"not ricevuta.")

                        except Exception as e:
                            # todo: should this kind of error shown to the user, probably not
                            # print(f"Errore durante l'upload di {pprint(out)} nel database: {str(e)}")
                            # error_inserts_data.append(xml)
                            print(f'EXCEPTION: {e}')
                            outs.append(out)
                            continue # to the next xml

                    successful_upload_count = len([res for res in outs if res['status'] == 'success'])
                    if successful_upload_count < 1:
                        st.warning("Nessuna nuova fattura caricata.")
                        st.session_state.is_processing = False
                    else:
                        st.success(f"Numero di fatture caricate correttamente: {successful_upload_count}")
                        st.session_state.is_processing = False

                    if st.button('Carica Altre Fatture', key="rerun", on_click=update_key):
                        st.session_state.is_processing = False
                        st.rerun()
                else:
                    st.error(f"Errore durante l'estrazione XML delle fatture: {error}")

def main():
    user_id, supabase_client, page_can_render = setup_page("Gestione Fatture")

    if page_can_render:
        content, space =  st.columns([1,1])
        with content:
            render_generic_xml_upload_section(supabase_client, user_id)


if __name__ == '__main__':
    main()
