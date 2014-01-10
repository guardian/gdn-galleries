import webapp2

class MainPage(webapp2.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write('Hello, webapp World!')

routes = [('/', MainPage)]

app = webapp2.WSGIApplication(routes,debug=True)