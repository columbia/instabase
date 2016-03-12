from flask import Flask, url_for, redirect, render_template, request
import grader

app = Flask(__name__)

### initialize the validator
validator = grader.createValidator("data/gold.csv")

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    scores = None
    if request.method == "POST":
        submission = request.form.get("predictions")
        try:
            scores = grader.grader_text(submission, validator)
        except grader.InputFormatError as e:
            print e.msg
    return render_template("dashboard.html", scores=scores)

@app.route('/leaderboard')
def leaderboard():
    return "this is the leaderboard"

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if email == "test@columbia.edu" and password == "123":
            return redirect(url_for('dashboard'))
    return render_template("login.html")

if __name__  == "__main__":
    app.run(debug=True)
