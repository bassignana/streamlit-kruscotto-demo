# test terminal command openssl smime -verify -noverify -in emesse/filename.sml.p7m -inform DER -out out.xml
# function to verify that the command is installed on the machine
# test that the file can be uploaded and modified
# find and modify the function that is responsible to create the files
# create a pytest test for it
# modify the function while i am at it for making it more testable and remove the old documentation.

# Night session for reading pytest / python module / pycharm docs.

import subprocess
import shutil
import streamlit as st
from pathlib import Path
import os

def verify_openssl_presence():
    openssl_path = shutil.which('openssl')
    if openssl_path:
        return f"OpenSSL found at: {openssl_path}"
    else:
        raise Exception("OpenSSL not found in PATH")


def p7m_to_file(input_path:str):
    """
    input_path:
    """

    output_dir = Path('p7m_to_xml_outputs')
    if output_dir.exists():
        shutil.rmtree(output_dir)

    # When running a single test manually: '/Users/bax/git/projects/streamlit-kruscotto-demo/pytest/tests'
    debug_info = os.getcwd()
    # will mkdir inside os.getcwd()
    output_dir.mkdir()

    input_path = Path(input_path)
    # .stem will just remove the last extension, leaving the correct file extension .xml
    output_filename = input_path.stem
    output_path = output_dir / output_filename

    subprocess.run([
        'openssl', 'smime',
        '-verify', '-noverify',
        '-in', str(input_path),
        '-inform', 'DER',
        '-out', str(output_path)
    ], check=True, capture_output=True, text=True)
    # return f"Content extracted successfully to {output_file}"

# p7m_to_file('emesse/filename.sml.p7m', 'out.xml')
#
# uploaded_files = st.file_uploader(
#     "Carica fatture in formato XML. Attualmente è consentito caricare fino a 100 fatture.",
#     type=['xml', 'p7m'],
#     accept_multiple_files=True,
# )
