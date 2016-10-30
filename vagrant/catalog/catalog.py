from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from itemdb_setup import Base, Items

app = Flask(__name__)

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(open('client_secret.json', 'r').read())['web']['client_id']

engine = create_engine('sqlite:///item.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create anti-forgery state token
@app.route('/login/')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE = state)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data
    print "pass one"
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        print "fail one"
        return response
    print "pass two"
    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response
    print "pass three"
    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print "pass four"
    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response
    print "pass five"
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# JSON APIs to view Restaurant Information
@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])

@app.route('/')
@app.route('/framework')
def landingPage():
    frameworks = session.query(Items).all()
    for f in frameworks:
        print f.category
        print f.id
        print f.description
        print f.name
    return render_template('Index.html', frameworks = frameworks)

@app.route('/new', methods=['GET', 'POST'])
def newPost():
    if request.method == 'POST':
        newItem = Items(name = request.form['name'], description = request.form['description'], category = request.form['framework'])
        session.add(newItem)
        session.commit()
        return redirect('/')
    else:
        return render_template('post.html',framework = "")

@app.route('/framework/<string:category>/')
def frameworks(category):
    print category
    frameworks = session.query(Items).filter_by(category=category)
    for f in frameworks:
        print f.name
    return render_template('category.html', frameworks=frameworks,category=category)

@app.route('/framework/<string:category>/<string:name>/')
def framework(category,name):
    print category
    framework = session.query(Items).filter_by(name=name).one()

    return render_template('framework.html', framework=framework)

@app.route('/framework/<string:category>/<string:name>/<int:id>/edit/', methods=['GET', 'POST'])
def frameworkEdit(category,name,id):
    framework = session.query(Items).filter_by(id=id).one()
    if request.method == 'POST':
        framework.name = request.form['name']
        framework.description = request.form['description']
        framework.category = request.form['framework']
        #session.add(framework)
        session.commit()
        return redirect('/')
    else:
        return render_template('post.html', framework=framework)

@app.route('/framework/<string:category>/<string:name>/<int:id>/delete/', methods=['GET', 'POST'])
def frameworkDelete(category,name,id):
    framework = session.query(Items).filter_by(id=id).one()
    if request.method == 'POST':
        session.delete(framework)
        session.commit()
        return redirect('/')
    else:
        return render_template('delete.html')


@app.route('/framework/<string:category>/<string:name>/JSON')
def frameworkJson(category,name):
    print category
    framework = session.query(Items).filter_by(name=name).one()
    return jsonify(Items=framework.serialize)

@app.route('/framework/<string:category>/JSON')
def frameworksJson(category):
    frameworks = session.query(Items).filter_by(category=category)

    return jsonify(Items=[i.serialize for i in frameworks])

@app.route('/delete/')
def delete():
    frameworks = session.query(Items).all()
    for f in frameworks:
        session.delete(f)
    session.commit()
    return redirect('/')


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)