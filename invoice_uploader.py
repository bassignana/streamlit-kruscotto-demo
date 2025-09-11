import streamlit as st
import datetime
from invoice_record_creation import extract_xml_records
from invoice_xml_processor import process_xml_list
from utils import setup_page

def render_generic_xml_upload_section(supabase_client, user_id):

    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    partita_iva_result = supabase_client.table('user_data').select('ud_partita_iva').eq('user_id',user_id).execute()
    partita_iva_azienda = partita_iva_result.data[0].get('ud_partita_iva', None)

    def update_key():
        st.session_state.uploader_key += 1

    # TODO: better error message, I should cast, not communicate the to the user.
    #  At best I can try to validate the format of the PIVA and tell the user
    #  that the PIVA inserted in its profile is incorrect.
    if not isinstance(partita_iva_azienda, str):
        st.error("La partita IVA dell'azienda e' in un formato inatteso.")

    # dynamic_key = str(datetime.datetime.now())
    uploaded_files = st.file_uploader(
        "Carica fatture in formato XML. Trascina qui le tue fatture o clicca per selezionare",
        type=['xml'],
        accept_multiple_files=True,
        help="Carica fino a 20 fatture XML contemporaneamente",
        key=f"uploader_{st.session_state.uploader_key}"
    )
    # NOTE: with the key, the state is_processing is not working anymore as intended,
    # But for now it can be a goog solution!.

    if uploaded_files:
        # st.toast(f"{len(uploaded_files)} file pronti per il caricamento.")

        if not st.session_state.is_processing:

            col1, space = st.columns([1, 3])

            with col1:
                st.info(f"{len(uploaded_files)} file pronti per il caricamento.")

                def callback():
                    st.session_state.is_processing = True
                process_button = st.button("Carica Fatture", type="primary",
                                           use_container_width=True, on_click=callback)

        # if process_button:
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

                                result = supabase_client.rpc('insert_record_fixed', {
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

                                result = supabase_client.rpc('insert_record_fixed', {
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
                    else:
                        st.success(f"Numero di fatture caricate correttamente: {successful_upload_count}")
                    # st.info("Clicca il pulsane qui sotto per aggiornare le tabelle una volta letti tutti gli avvisi.")
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
