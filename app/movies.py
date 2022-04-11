#!/usr/bin/env python
import os
import time
import json

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
    unseen = []
    watched = []
    for movie, status in movies_d.items():
        if status: #this means its already watched
            watched.append(movie)
            continue
        unseen.append(movie)

    return flask.render_template(
        'movies.html',
        movies = unseen,
        watched = watched,
    )

@app.route('/edit', methods = ['GET'])
@flask_login.login_required
def edit():
    movies_d = fsdb.get_as_dict()
    unseen = []
    watched = []
    for movie, status in movies_d.items():
        if status: #this means its already watched
            watched.append(movie)
            continue
        unseen.append(movie)

    return flask.render_template(
        'edit.html',
        movies = unseen,
        watched = watched,
    )

@app.route('/movies/add', methods = ['POST'])
@flask_login.login_required
def add_movie():
    form = flask.request.form
    movie = form.get('movie', None)
    fsdb.set(movie, False)
    return flask.redirect(flask.url_for('movies'))

@app.route('/movies/delete', methods = ['DELETE'])
@flask_login.login_required
def delete_movie():
    try:
        form = flask.request.get_json()
        movie = form.get('movie', None)
    except Exception:
        return 'couldnt parse json', 400

    fsdb.set(movie, None)
    return 'ok', 200

@app.route('/movies/edit', methods = ['PUT'])
@flask_login.login_required
def edit_movie():
    try:
        form = flask.request.get_json()
        movie = form.get('movie', None)
    except Exception:
        return 'couldnt parse json', 400

    fsdb.set(movie, True)
    return 'ok', 200

@app.route('/apple-touch-icon.png', methods = ['GET'])
def apple_touch():
    '''
    pretty sure there is a better way to do this
    '''
    return flask.send_from_directory(
        os.path.join(app.root_path, 'static'),
        'movies.png',
        mimetype='image/png'
    )


if __name__=="__main__":
    app.run(debug=True, host='0.0.0.0')
