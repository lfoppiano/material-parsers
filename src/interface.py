from tempfile import NamedTemporaryFile

from flask import Flask, render_template, request
from grobid_client_generic import grobid_client_generic

app = Flask(__name__)


@app.route('/version')
def version():
    return '0.0.1'


@app.route('/')
def root():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process_pdf():
    file = request.files['input']
    grobid = grobid_client_generic(config_path="./config.json")
    tf = NamedTemporaryFile()
    tf.write(file.read())
    return grobid.process_pdf(tf.name, 'processPDF', headers={'Accept': 'application/json'})



if __name__ == '__main__':
    app.run(host='0.0.0.0')
