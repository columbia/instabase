from flask import Flask, url_for, flash, redirect, render_template
from flask import request, g, jsonify, abort, session, escape
from datetime import datetime
import pytz
import grader
from functools import wraps
import argparse
import requests
import os
import string
from random import sample, choice
import hashlib
import rethinkdb as r
from rethinkdb.errors import RqlRuntimeError, RqlDriverError

app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

###################
## CONFIGURATION ##
###################
RDB_HOST = os.environ.get('RDB_HOST') or 'localhost'
RDB_PORT = os.environ.get('RDB_PORT') or 28015
MAILGUN_KEY = os.environ.get("MAILGUN_KEY")
DB = 'instabase'
MAILGUN_URL = "https://api.mailgun.net/v3/timelogger.mailgun.org/messages"

### initialize the validator
validator = grader.createValidator("data/gold.csv")

###################
###### UTILS ######
###################
def generate_password(uni,length=18):
    chars = string.letters + string.digits
    rand_pass = ''.join([choice(chars) for i in range(8)])
    sha = hashlib.sha1(uni).hexdigest()
    return sha[:10] + rand_pass

def is_columbia_email(email):
    email = email.strip()
    return email and email.split('@')[-1] == "columbia.edu"

def send_email(email, password):
    return requests.post(MAILGUN_URL,
        auth=("api", MAILGUN_KEY),
        data={"from": "do-not-reply@instabase-csds.com", "to": [email],
              "subject": "Password for Instabase",
              "text": "Hello, your password for instabase is: " + password })

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            flash("You need to login to view this page", "danger")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

####################
####### DB #########
####################
def db_setup():
    connection = r.connect(host=RDB_HOST, port=RDB_PORT)
    try:
        r.db_create(DB).run(connection)
        r.db(DB).table_create('leaderboard').run(connection)
        r.db(DB).table_create('submissions').run(connection)
        r.db(DB).table_create('users').run(connection)
        print 'Database setup completed. Now run the app without --setup.'
    except RqlRuntimeError:
        print 'App database already exists. Run the app without --setup.'
    finally:
        connection.close()

def db_drop():
    connection = r.connect(host=RDB_HOST, port=RDB_PORT)
    try:
        r.db_drop(DB).run(connection)
        print "Database dropped."
    except:
        print "Error in dropping database"
    finally:
        connection.close()

@app.before_request
def before_request():
    try:
        g.rdb_conn = r.connect(host=RDB_HOST, port=RDB_PORT, db=DB)
    except RqlDriverError:
        abort(503, "No database connection could be established.")

@app.teardown_request
def teardown_request(exception):
    try:
        g.rdb_conn.close()
    except AttributeError:
        pass


####################
#### ROUTES ########
####################
@app.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    scores = None
    if request.method == "POST":
        predictions = request.form.get("predictions")
        code = request.form.get("code")
        try:
            scores = grader.grader_text(predictions, validator)
            email = 'bkj2111@columbia.edu'
            nyc = pytz.timezone('America/New_York')

            inserted = r.table('submissions').insert({
                'timestamp': nyc.localize(datetime.now(), is_dst=False),
                'email': email,
                'predictions': predictions,
                'code': code,
                'precision': scores['precision'],
                'recall': scores['recall'],
                'F1': scores['F1']
            }).run(g.rdb_conn)

            if inserted['generated_keys']:
                flash("Submission Successful!", "success")
            else:
                flash("Submission Unsuccessful!", "danger")
        except grader.InputFormatError as e:
            flash(e.msg, "danger")
    return render_template("dashboard.html", scores=scores)

@app.route('/leaderboard')
@login_required
def leaderboard():
    return "this is the leaderboard"

@app.route('/signup', methods=["POST"])
def signup():
    email = request.form.get('email')
    name = request.form.get("name")
    password = None
    if not is_columbia_email(email):
        flash("Not a valid columbia ID!", "danger")
    else:
        email = email.strip()
        curr = r.table('users').filter(r.row["email"].eq(email)).run(g.rdb_conn)
        if curr.items:
            user = curr.items[0]
            password = user["password"]
        else:
            password = generate_password(email)
            inserted = r.table('users').insert({
                'email': email,
                'name': name,
                'password': password
            }).run(g.rdb_conn)
            if inserted["generated_keys"]:
                password = password
        resp = send_email(email, password)
        if resp.status_code == 200:
            flash("Email sent! Check your inbox for your login details", "success")
        else:
            flash("Error sending email. Please try again or contact admin", "danger")
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    session.pop('email', None)
    flash("You have successfully logged out!", "success")
    return redirect(url_for('login'))

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        curr = r.table('users') \
                .filter(r.row["email"].eq(email)) \
                .filter(r.row["password"].eq(password)) \
                .run(g.rdb_conn)
        if not curr.items:
            flash("Invalid email / password combination", "danger")
            return render_template("login.html")
        session['email'] = email
        flash("You have successfully logged in!", "success")
        return redirect(url_for('dashboard'))
    return render_template("login.html")

if __name__  == "__main__":
    parser = argparse.ArgumentParser(description='Run the instabase app')
    parser.add_argument('--setup', dest='run_setup', action='store_true')
    parser.add_argument('--drop', dest='run_drop', action='store_true')
    args = parser.parse_args()
    if args.run_setup:
        db_setup()
    elif args.run_drop:
        db_drop()
    else:
        app.run(debug=True)
