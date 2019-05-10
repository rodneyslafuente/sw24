import requests
import urllib.parse

from flask import redirect, render_template, request
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

def user_info(ip):

    # Developer API key
    API_KEY= "e7d27372397245e956a5f33fe266d281"

    # location search end point
    url = 'http://api.ipstack.com/' + ip + '?access_key=' + API_KEY

    # Call the API
    response = requests.request('GET', url)

    return response.json()


def businesses(ip):

    # Developer API key
    API_KEY= "vkC0ujXxFu5l9v5zvct794_H8c-wqPjE2DFWY1y8cjlWVTVhx2BMoBK-A2Y5LYutYW58NNX900fwkG3Qr8Vke8BT1f7ybMpYr82wfvsKD0DF0RVkf-ljxmFds4jUXHYx"

    info = user_info(ip)

    # What you are searching for
    DEFAULT_TERM = 'contraceptives'

    # Coordinates
    LATITUDE = info['latitude']
    LONGITUDE = info['longitude']

    # Maximum number of results to return
    SEARCH_LIMIT = 5

    # Business search end point
    url = 'https://api.yelp.com/v3/businesses/search'
    # Heahder should contain the API key
    headers = {'Authorization': 'Bearer {}'.format(API_KEY)}
    # Search parameters
    url_params = {
      'term': DEFAULT_TERM,
      'longitude' : LONGITUDE,
      'latitude' : LATITUDE,
      'limit': SEARCH_LIMIT
      }

    # Call the API
    response = requests.request('GET', url, headers=headers, params=url_params)

    # To get a better understanding of the structure of
    # the returned JSON object refer to the documentation
    # For each business, print name, rating, location and phone
    return response.json()["businesses"]


