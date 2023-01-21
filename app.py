from minify import subsettor, character_list
import os
from flask import Flask, redirect, url_for, request, flash, session, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_mail import Mail, Message
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from fontTools.ttLib import TTFont
from uuid import uuid4
from threading import Thread
from shutil import make_archive, rmtree
from zipfile import ZipFile
from io import BytesIO

load_dotenv()

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'ttf', 'otf'}
app.secret_key = "secret"
app.config['UPLOAD_FOLDER'] = './uploads'

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
mail = Mail(app)


# setup flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# setup model User which manages the accounts
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(128))
    email = db.Column(db.String(64), unique=True)
    def __init__(self, username, password, email):
        self.username = username
        self.password = self.set_password(password)
        self.email = email
    def set_password(self, password):
        self.pw_hash = generate_password_hash(password)
        return self.pw_hash
    def check_password(self, password, pw_hash):
        return check_password_hash(pw_hash, password)
    def __repr__(self):
        return '<User %r>' % (self.username)

# setup model Font which manages the fonts
class Font(db.Model):
    __tablename__ = 'fonts'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(64), unique=True)
    font_name = db.Column(db.String(64))
    font_weight = db.Column(db.Integer)
    user_id = db.Column(db.String(64), db.ForeignKey('users.username'))
    user = db.relationship('User', backref=db.backref('fonts', lazy='dynamic'))
    def __init__(self, filename, user_id, font_name, font_weight):
        self.filename = filename
        self.user_id = user_id
        self.font_name = font_name
        self.font_weight = font_weight
    def __repr__(self):
        return '<Font %r>' % (self.filename)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_authorized_filename(filename):
    return filename.rsplit('.', 1)[0].lower() + '-' + str(uuid4()) + '.' +filename.rsplit('.', 1)[1].lower()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/postfont', methods=['POST', 'GET'])
@login_required
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
    # if ttf exists
    if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "rb") as f:
            font = TTFont(f)
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

    return render_template('fontconfig.html', filename=filename, show_render_button=show_render_button, show_download_button=show_download_button)


@app.route('/fonts/<filename>/write', methods=['POST'])
def writeFonts(filename):
    font_name = request.form['font_name']
    font_weight = request.form['font_weight']
    db.session.add(Font(filename=filename, font_name=font_name, font_weight=font_weight, user_id=current_user.username))
    db.session.commit()
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), "rb") as f:
        font = TTFont(f)
        base_chars = character_list(font)
        list_of_chars = [base_chars[i:i+300] for i in range(0, len(base_chars), 300)]
    os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()))
    def make_subset():
        for i, chars in enumerate(list_of_chars):
            subsettor(os.path.join(app.config['UPLOAD_FOLDER'], filename), "".join(chars), str(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()+ "/" + filename.rsplit('.', 1)[0].lower() + '-' + str(i) + '.woff2')))
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()+ "/" + font_name +'.css'), 'w') as f:
            for i, chars in enumerate(list_of_chars):
                f.write("@font-face {\n")
                f.write("font-family: '" + font_name + "';\n")
                f.write("font-weight: " + font_weight + ";\n")
                f.write("src: url('" + filename.rsplit('.', 1)[0].lower() + '-' + str(i) + ".woff2') format('woff2');\n")
                f.write("unicode-range: " + ",".join([f'U+{hex(ord(c))[2:]}' for c in chars]) + ";\n")
                f.write("}\n")
            # write commentouted copyright
            f.write("/*\n")
            f.write("TypeShrinkで生成されました。Generated with TypeShrink.\n")
            f.write("*/\n")
        make_archive(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()), 'zip', os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()))
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        rmtree(os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower()))
        # write to database
    t = Thread(target=make_subset)
    t.start()
    return redirect(url_for('getFonts', filename=filename))


@app.route('/fonts/<filename>/download')
def downloadFiles(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0].lower() + '.zip')


# create user loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        registered_user = User.query.filter_by(username=username).first()
        if registered_user is None:
            flash('Username is invalid' , 'error')
            return redirect(url_for('login'))
        if not registered_user.check_password(password, registered_user.password):
            flash('Password is invalid' , 'error')
            return redirect(url_for('login'))
        login_user(registered_user)
        flash('Logged in successfully')
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        user = User(username=username, email=email, password=password)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Thanks for registering')
        return redirect(url_for('login'))
    return render_template('signup.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
