import configuration

import webapp2
import jinja2
import os
import json
import logging

import headers

from webapp2 import abort

from google.appengine.api.urlfetch import fetch
from google.appengine.api import memcache
from urlparse import urlparse
import urllib

jinja_environment = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")))

CONTENT_API_HOST = configuration.lookup('CONTENT_API_HOST', 'content.guardianapis.com')
CONTENT_API_KEY = configuration.lookup('CONTENT_API_KEY')

#http://content.guardianapis.com/uk/gallery/2012/dec/18/queen-visits-downing-street-pictures?format=json&show-related=true&tag=type%2Fgallery&order-by=newest

def related_galleries(page_url, recent = None):
	params = {"format" : "json",
		"show-related" : "true",
		"tag" : "type/gallery",
		"order-by" : "newest",
		"show-fields" : "thumbnail,headline",
		"page-size" : "24",}

	if CONTENT_API_KEY:
		params["api-key"] = CONTENT_API_KEY


	if recent:
		last30days = (datetime.date.today() + datetime.timedelta(-30)).isoformat()
		params['from-date'] = last30days

	parsed_url = urlparse(page_url)

	content_path = parsed_url.path

	cache_key = content_path

	if recent:
		cache_key = cache_key + ".recent"

	cached_content = memcache.get(cache_key)

	if cached_content:
		return json.loads(cached_content)

	content_api_url = "http://" + CONTENT_API_HOST + content_path + "?" + urllib.urlencode(params)

	#logging.info(content_api_url)

	result = fetch(content_api_url, deadline = 9)

	if not result.status_code == 200:
		logging.warning("CAPI returned status code: %d" % result.status_code)
		return []

	data = json.loads(result.content)

	#logging.info(data)

	if not "relatedContent" in data["response"]:
		logging.warning("No relatedContent present in response")
		return []

	related_content = [item for item in data["response"]["relatedContent"] if "fields" in item and "thumbnail" in item['fields']]

	memcache.add(cache_key, json.dumps(related_content), 10 * 60)

	return related_content

def all_images(page_url):
	params = {"format" : "json",
		"show-media" : "picture",
		"order-by" : "newest",
		"show-fields" : "thumbnail,headline",}

	if CONTENT_API_KEY:
		params["api-key"] = CONTENT_API_KEY

	parsed_url = urlparse(page_url)

	content_api_url = "http://" + CONTENT_API_HOST + parsed_url.path + "?" + urllib.urlencode(params)

	#logging.info(content_api_url)

	result = fetch(content_api_url, deadline = 9)

	if not result.status_code == 200:
		return []

	data = json.loads(result.content)

	#logging.info(data)

	return data.get("response", {}).get("content", {}).get("mediaAssets", [])

class RelatedGalleries(webapp2.RequestHandler):
	def get(self, target='4'):
		template = jinja_environment.get_template("related-galleries.html")

		data = {"title" : "More galleries",}
		if "page-url" in self.request.params:
			data["galleries"] = related_galleries(self.request.params["page-url"])[:int(target)]
		else:
			abort(400, "No page url specified")

		headers.set_cors_headers(self.response)
		self.response.out.write(template.render(data))

class RecentRelatedGalleries(webapp2.RequestHandler):
	def get(self):
		template = jinja_environment.get_template("related-galleries.html")

		data = {"title" : "More galleries",}
		if "page-url" in self.request.params:
			data["galleries"] = related_galleries(self.request.params["page-url"], recent=True)[:4]

		headers.set_cors_headers(self.response)
		self.response.out.write(template.render(data))

class AllImages(webapp2.RequestHandler):
	def get(self):
		template = jinja_environment.get_template("all-images-gallery.html")
		template_values = {}

		if "page-url" in self.request.params:
			template_values["images"] = all_images(self.request.params["page-url"])

		headers.set_cors_headers(self.response)
		self.response.out.write(template.render(template_values))

class RelatedGalleriesBox(webapp2.RequestHandler):
	def get(self, target='12'):
		template = jinja_environment.get_template("components/gallery-box.html")

		headers.set_cors_headers(self.response)

		data = {"title" : "More galleries",}
		if "page-url" in self.request.params:
			gallery_data = related_galleries(self.request.params["page-url"])

			if not gallery_data:
				abort(404, "No related content")

			data["galleries"] = gallery_data[:int(target)]
		else:
			abort(400, "No page url specified")

		self.response.out.write(template.render(data))

app = webapp2.WSGIApplication([
	('/components/galleries/related', RelatedGalleries),
	('/components/galleries/related/(\d+)', RelatedGalleries),
	('/components/galleries/related/recent', RecentRelatedGalleries),
	('/components/galleries/all-pictures', AllImages),
	('/components/galleries/related/box', RelatedGalleriesBox),],
	debug=True)