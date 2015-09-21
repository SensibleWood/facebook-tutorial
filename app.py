#!/usr/bin/env python
# coding=utf-8

__author__ = "Chris Wood"

from flask_bootstrap import Bootstrap

from json import loads, dumps
from urllib3 import HTTPSConnectionPool, disable_warnings
from urllib.parse import parse_qs

import logging
import flask

app = flask.Flask(__name__)
app.config.from_object(__name__)
app.secret_key = "Secret key"
Bootstrap(app)

FACEBOOK_APP_ID="YOUR_APP_ID"
FACEBOOK_APP_SECRET="YOUR_APP_SECRET"
GRAPH_API_VERSION="v2.4"
REDIRECT_URI="http://127.0.0.1:8080/callback"

TOKENS = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
disable_warnings()

class NotAuthorizedException(Exception):
    pass


class FacebookConnection(HTTPSConnectionPool):
    """
    Convenience class to that wraps connection and call to Graph API
    """
    def __init__(self):
        super(FacebookConnection, self).__init__('graph.facebook.com')

    def __call__(self, method, url, token, http_headers, request_body):
        if http_headers is None:
            http_headers = {}

        if token is not None:
            http_headers["Authorization"] = "Bearer %s" % token

        return self.urlopen(method, url, headers=http_headers, body=request_body)

FACEBOOK_CONNECTION=FacebookConnection()

# OAuth functions


def get_app_token():
    """
    Get an app token based on app ID and secret

    :return:
    """
    try:
        response = FACEBOOK_CONNECTION(
            'GET',
            '/oauth/access_token?client_id=%s&client_secret=%s&grant_type=client_credentials'
            % (FACEBOOK_APP_ID, FACEBOOK_APP_SECRET),
            None, None, None)

        return parse_qs(response.data.decode("utf-8"))["access_token"]
    except KeyError:
        logging.log(logging.ERROR, response.data)
        raise NotAuthorizedException("Authorization error", "App access token not found")
    except:
        raise


def get_user_token(code):
    try:
        response = FACEBOOK_CONNECTION(
            'GET',
            '/%s/oauth/access_token?client_id=%s&redirect_uri=%s&client_secret=%s&code=%s'
            % (GRAPH_API_VERSION, FACEBOOK_APP_ID, REDIRECT_URI, FACEBOOK_APP_SECRET, code),
            None, None, None)
        print(response.data.decode("utf-8"))

        return loads(response.data.decode("utf-8"))["access_token"]
    except KeyError:
        logging.log(logging.ERROR, response.data)
        raise NotAuthorizedException("Authorization error", "User access token not found")
    except:
        raise

# App routes


@app.route("/")
def serve_home():
    """
    Serves up the home page

    :return: Renders the home page template
    """

    # Check whether the user has authorized the app, if authorized login button will not be displayed
    user_authorized = True if "user_token" in TOKENS else False

    return flask.render_template("index.html", authorized=user_authorized)


@app.route("/authorize")
def authorize_facebook():
    """
    Redirects the user to the Facebook login page to authorize the app:
    - response_type=code
    - Scope requests is to post updates on behalf of the user and read their stream

    :return: Redirects to the Facebook login page
    """
    return flask.redirect("https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&scope=publish_actions"
                    % (FACEBOOK_APP_ID, REDIRECT_URI))


@app.route("/callback")
def handle_callback():
    """
    Handles callback after user authorization of app, calling back to exchange code for access token

    :return:
    """
    global TOKENS

    try:
        TOKENS["user_token"] = get_user_token(flask.request.args.get("code"))

        return flask.redirect("/")
    except NotAuthorizedException:
        return 'Access was not granted or authorization failed', 403
    except:
        raise


@app.route("/helloworld", methods=["POST"])
def hello_world():
    global TOKENS
    lat_lng = None

    # Make sure there is a token
    try:
        token = TOKENS["user_token"]
    except KeyError:
        return 'Not authorized', 401

    # Get a place id to include in the post, search for coffee within 10000 metres and grab first returned
    try:
        response = FACEBOOK_CONNECTION(
            'GET',
            '/%s/search?q=coffee+shop&type=place&center=%s,%s&distance=10000'
            % (GRAPH_API_VERSION, flask.request.args.get("lat"), flask.request.args.get("lng")),
            token, None, None)

        if response.status != 200:
            logging.log(logging.ERROR, response.data)
            return 'Unexpected HTTP return code from Facebook: %s' % response.status, response.status

    except Exception as e:
        logging.log(logging.ERROR, str(e))
        return 'Unknown error calling Graph API', 502

    # Attempt to add place to post (if one is returned)
    try:
        places = loads(response.data.decode("utf-8"))
        post = {
            "message": "Heading+out+for+coffee.+Hello+World%21",
            "place": places["data"][0]["id"]
        }
        lat_lng = {
            "name": places["data"][0]["name"],
            "lat": places["data"][0]["location"]["latitude"],
            "lng": places["data"][0]["location"]["longitude"]
        }

    except (KeyError, IndexError):
        post = {
            "message": "Staying+home+for+coffee.+Goodbye+World%21"
        }

    try:
        response = FACEBOOK_CONNECTION('POST', '/%s/me/feed' % GRAPH_API_VERSION, token,
                                       None, '&'.join(list("%s=%s" % (key,value) for key, value in post.items())))

        if response.status != 200:
            logging.log(logging.ERROR, response.data)
            return 'Unexpected HTTP return code from Facebook: %s' % response.status, response.status
    except Exception as e:
        logging.log(logging.ERROR, str(e))
        return 'Unknown error calling Graph API', 502

    if lat_lng is None:
        return '', 201
    else:
        return flask.jsonify(**lat_lng), 201

if __name__ == '__main__':
    # Register an app token at start-up (purely as validation that configuration for Facebook is correct)
    TOKENS["app_token"] = get_app_token()
    app.run(host="0.0.0.0", port=8080, debug=True)