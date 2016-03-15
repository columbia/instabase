# -*- coding: utf-8 -*-

"""
Submission Server
=====

A simple app that allow students to upload their ER scores and get results
"""
from flask import Flask, url_for, flash, redirect, render_template
from flask import request, g, jsonify, abort, session, escape
from flask_sockets import Sockets
import logging
from datetime import datetime
import gevent
import pytz
import json
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

###################
## CONFIGURATION ##
###################
RDB_HOST = os.environ.get('RDB_HOST') or 'localhost'
RDB_PORT = os.environ.get('RDB_PORT') or 28015
MAILGUN_KEY = os.environ.get("MAILGUN_KEY")
DB = 'instabase'
MAILGUN_URL = "https://api.mailgun.net/v3/timelogger.mailgun.org/messages"

### init
app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
validator = grader.createValidator("data/gold.csv")

sockets = Sockets(app)

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

class LeaderboardTracker(object):
    """ A backend for storing clients for websocket connections """

    def __init__(self):
        self.clients = list()
        self.conn = r.connect(host=RDB_HOST, port=RDB_PORT, db=DB)

    def register(self, client):
        self.clients.append(client)
        print "registering a new client. total clients:", len(self.clients)
        msg = { "msg": "connected", "type": "INFO" }
        client.send(json.dumps(msg))

    def send(self, client, data):
        try:
            msg = { "msg": "leaderboard updated", "type": "UPDATE" }
            client.send(json.dumps(msg))
            print "data sent to client"
        except Exception:
            print "some issue. removing client"
            self.clients.remove(client)
            print "removed a client. total clients:", len(self.clients)

    def run(self):
        self.cursor = r.table('leaderboard').changes().run(self.conn)
        for document in self.cursor:
            for client in self.clients:
                gevent.spawn(self.send, client, document)

    def start(self):
        print u'Started listening for changes on leaderboard'
        gevent.spawn(self.run)

tracker = LeaderboardTracker()
tracker.start()

####################
#### ROUTES ########
####################
@app.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    scores = None
    email = session['email']
    history = r.table('submissions')\
                .filter(r.row["email"].eq(email))\
                .order_by(r.desc('timestamp')) \
                .run(g.rdb_conn)
    if request.method == "POST":
        predictions = request.form.get("predictions")
        code = request.form.get("code")
        try:
            scores = grader.grader_text(predictions, validator)
            nyc = pytz.timezone('America/New_York')
            submission = {
                'timestamp': nyc.localize(datetime.now(), is_dst=False),
                'email': email,
                'predictions': predictions,
                'code': code,
                'precision': scores['precision'],
                'recall': scores['recall'],
                'F1': scores['F1']
            }
            inserted = r.table('submissions').insert(submission).run(g.rdb_conn)


            ## leaderboard
            best = r.table('leaderboard')\
                    .filter(r.row['email'].eq(email))\
                    .run(g.rdb_conn)

            name = r.table('users')\
                    .filter(r.row['email'].eq(email))\
                    .get_field('name').run(g.rdb_conn)

            if not best.items:
                ins = r.table('leaderboard').insert({
                    "name": name.items[0],
                    "email": email,
                    "F1": scores["F1"]
                }).run(g.rdb_conn)
            else:
                best = best.items[0]
                if scores["F1"] > best["F1"]:
                    # update the best score
                    up = r.table('leaderboard')\
                          .filter(r.row["email"].eq(email))\
                          .update({"F1": scores["F1"]}).run(g.rdb_conn)
            if inserted['generated_keys']:
                flash("Submission Successful!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Submission Unsuccessful!", "danger")
        except grader.InputFormatError as e:
            flash(e.msg, "danger")
    return render_template("dashboard.html", history=history, page="dashboard", logged_in=True)


@app.route('/leaderboard.json')
@login_required
def api_leaderboard():
    leaders = r.table('leaderboard').order_by(r.desc('F1')).run(g.rdb_conn)
    email = session["email"]
    scores = [s["F1"] for s in leaders]
    try:
        rank = [l["email"] for l in leaders].index(email) + 1
    except ValueError:
        rank = 0
    return jsonify({
        "leaders": leaders,
        "rank": rank,
        "email": email,
        "scores": scores
    })

@app.route('/leaderboard')
@login_required
def leaderboard():
    return render_template("leaderboard.html", page="leaderboard", logged_in=True)

@app.route('/submission/<string:sub_id>')
@login_required
def submission(sub_id):
    sub = r.table('submissions').get(sub_id).run(g.rdb_conn)
    if not sub:
        abort(404)
    return render_template("submission.html", sub=sub, page="submission",logged_in=True)

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
        return redirect(url_for('dashboard'))
    return render_template("login.html", page="login", logged_in=False)


#### WEBSOCKET ROUTE
@sockets.route('/receive')
def outbox(ws):
    tracker.register(ws)
    while not ws.closed:
        gevent.sleep(0.1)


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
        app.run(host="0.0.0.0", debug=True)
