import urlparse
import urllib
import logging

from google.appengine.api.urlfetch import fetch
from google.appengine.api import memcache

import configuration

CONTENT_API_HOST = configuration.lookup('CONTENT_API_HOST', 'content.guardianapis.com')
CONTENT_API_KEY = configuration.lookup('CONTENT_API_KEY')

def content_id(url):
	parsed_url = urlparse.urlparse(url)
	return parsed_url.path

def read(content_id, params = None):
	client = memcache.Client()

	url = "http://%s%s" % (CONTENT_API_HOST, content_id)

	if CONTENT_API_KEY and not "api-key" in params:
		params['api-key'] = CONTENT_API_KEY
		
	if params:
		url = url + "?" + urllib.urlencode(params)

	logging.info(url)

	cached_data = client.get(url)

	if cached_data: return cached_data

	result = fetch(url)

	if not result.status_code == 200:
		logging.warning("Content API read failed: %d" % result.status_code)
		return None

	client.set(url, result.content, time = 60 * 15)

	return result.content

def response_ok(response):
	if not response:
		return False

	if not "response" in response:
		return False

	if not "status" in response["response"]:
		return False

	if not response["response"]["status"] == "ok":
		return False

	if not "content" in response["response"]:
		return False

	return True