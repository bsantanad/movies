#!/usr/bin/env python
import os
import time

import flask
import flask_login
import dotenv

import db
import user_c
import auth_userdb

dotenv.load_dotenv()

fsdb_path = os.environ.get('FSDB', '/db')
userdb_path = os.environ.get('USERDB', '/userdb')

fsdb = db.fsdb_symlink_c(fsdb_path)
userdb = auth_userdb.driver(userdb_path)

app = flask.Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', None)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
# None means that the cookie will not contain information about
# the IP address where the login came from. We want to be able to
# carry our login information while the machine changes IP
# address.
# https://flask-login.readthedocs.io/en/latest/#session-protection
login_manager.session_protection = None

@login_manager.user_loader
def load_user(userid):
    """
    Called by the login manager when looking for information about
    a given user ID
    """
    return user_c.User.search_user(userid)

@app.route('/')
def index():
    return flask.render_template('index.html')

@app.route('/login', methods = ['POST'])
def login():
    form = flask.request.form
    username = form.get('username', None)
    password = form.get('passwd', None) #FIXME this should be the hash

    try:
        userdb.login(username, password)
    except Exception as e:
        return "bad login", 401

    user = user_c.User(username)
    flask_login.login_user(user, remember = True)
    return flask.redirect(flask.url_for('movies'))

@app.route('/movies', methods = ['GET'])
@flask_login.login_required
def movies():
    movies_d = fsdb.get_as_dict()
    tmp = []
    for movie, _ in movies_d.items():
        tmp.append(movie)
    return flask.render_template('movies.html', movies = tmp)

@app.route('/movies/add', methods = ['POST'])
@flask_login.login_required
def add_movie():
    form = flask.request.form
    movie = form.get('movie', None)
    fsdb.set(movie, False)
    return flask.redirect(flask.url_for('movies'))

if __name__=="__main__":
    app.run(debug=True, host='0.0.0.0')
