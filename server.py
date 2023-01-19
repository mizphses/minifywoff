from minify import subsettor, character_list, suggestion_charset
import os
from flask import Flask, redirect, url_for, request, flash, session, render_template, send_from_directory
from werkzeug.utils import secure_filename
from fontTools.ttLib import TTFont
from uuid import uuid4
from threading import Thread
from shutil import make_archive, rmtree

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'ttf', 'otf'}
app.secret_key = "secret"
app.config['UPLOAD_FOLDER'] = './uploads'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_authorized_filename(filename):
    return filename.rsplit('.', 1)[0].lower() + '-' + str(uuid4()) + '.' +filename.rsplit('.', 1)[1].lower()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/postfont', methods=['POST', 'GET'])
def postfont():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('postfont.html', error="ファイルがありません。")
        file = request.files['file']
        if file.filename == '':
            return render_template('postfont.html', error="ファイルがありません。")
        if file and allowed_file(file.filename):
            filename =  create_authorized_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('getFonts', filename=filename))
        else:
            return render_template('postfont.html', error="正しくないファイル形式です")
    return render_template('postfont.html', error=None)

@app.route('/fonts/<filename>', methods=['GET', 'POST'])
def getFonts(filename):
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "rb") as f:
        font = TTFont(f)
        charset = suggestion_charset(character_list(font))
        base_chars = character_list(font)
        list_of_chars = [base_chars[i:i+1000] for i in range(0, len(base_chars), 1000)]
        # show render button if the font is not been zip and not under processing which the folder was generated
        if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower() + '.zip')) or os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower())):
            show_render_button = False
        else:
            show_render_button = True
        if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower() + '.zip')):
            show_download_button = True
        else:
            show_download_button = False
    return render_template('fontconfig.html', filename=filename, charset=charset, show_render_button=show_render_button, show_download_button=show_download_button)


@app.route('/fonts/<filename>/write', methods=['POST'])
def writeFonts(filename):
    font_name = request.form['font_name']
    font_weight = request.form['font_weight']
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "rb") as f:
        font = TTFont(f)
        charset = suggestion_charset(character_list(font))
        base_chars = character_list(font)
        list_of_chars = [base_chars[i:i+300] for i in range(0, len(base_chars), 300)]
    os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()))
    def make_subset():
        for i, chars in enumerate(list_of_chars):
            subsettor(os.path.join(app.config['UPLOAD_FOLDER'], filename), "".join(chars), str(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()+ "/" + filename.rsplit('.', 1)[0].lower() + '-' + str(i) + '.woff2')))
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower() + "/" + filename.rsplit('.', 1)[0].lower() + '.css'), 'w') as f:
            for i, chars in enumerate(list_of_chars):
                f.write("@font-face {\n")
                f.write("font-family: '" + font_name + "';\n")
                f.write("font-weight: " + font_weight + ";\n")
                f.write("src: url('" + filename.rsplit('.', 1)[0].lower() + '-' + str(i) + ".woff2') format('woff2');\n")
                f.write("}\n")
        make_archive(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()), 'zip', os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()))
        rmtree(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()))

    t = Thread(target=make_subset)
    t.start()
    return redirect(url_for('getFonts', filename=filename))


@app.route('/fonts/<filename>/download')
def downloadFiles(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower() + ".zip", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
