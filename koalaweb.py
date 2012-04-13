# -*- coding: utf-8 -*-

import os, types, inspect, urlparse, collections
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect
from werkzeug.serving import run_simple

from jinja2 import Environment, FileSystemLoader

__version__ = "0.1a2"
__author__ = "Xu Ke"
__email__ = "support@tuoxie.me"
__url__ = "https://github.com/tuoxie007/koalaweb"

class Model(dict):
  def __getattr__(self, key):
    if self.has_key(key):
      return self[key]
    return None

  def __setattr__(self, key, value):
    self[key] = value

"""
Web Framework for lazy man like koala

* Itelligent route
* Easy context access
* Powerful template engine

Appoint is greater than configuration.

"""

try:
    import app as approot
except:
    approot = object()

try:
    import koalaconf as config
except:
    class Config(dict):
        def __getattr__(self, key):
            return self[key]
        def __setattr__(self, key, value):
            self[key] = value
    config = Config(templates_dir="templates",
                    root_path="/",
                    dict_to_json=True,
                    use_debugger=True,
                    use_reloader=True)

jinja_env = Environment(loader=FileSystemLoader(os.path.join(os.getcwd(), 
                                                             config.templates_dir)), 
                        autoescape=False)

def format_datetime(value, format=None):
    if not value: return ""
    if not format: format = "%Y-%m-%d %H:%M:%S"
    return value.strftime(format)

def markdown(content, html='off'):
    if not content: return ""
    if html == "on": return content
    import markdown
    return markdown.markdown(content)

jinja_env.filters['datetime'] = format_datetime
jinja_env.filters['markdown'] = markdown

def is_mobile():
    user_agent = header("User-Agent")
    if user_agent:
        return user_agent.lower().find("mobile") >= 0

def user_agent():
    ua  = header("User-Agent")
    return {"is_mobile": us.lower().find("mobile") >= 0,
            "is_ie": us.lower().find("msid") >= 0}

def redirect(location):
    return werkzeug.utils.redirect(config.root_path + location)

def render_template(template_name, **context):
  tmpl = jinja_env.get_template(template_name)
  tmpl_context = {"base_url": config.root_path}
  tmpl_context.update(context)
  return tmpl.render(tmpl_context)

request = None
def header(key=None):
  if key is None:
    return request.headers
  elif key is True:
    return dict(request.headers)
  return request.headers[key] if request.headers.has_key(key) else None

def rawdata():
  return request.data

def query(key=None):
  if key is None:
    return request.values
  elif key is True:
    return dict(request.values)
  return request.values[key] if request.values.has_key(key) else None

def form(name=None):
  data = Model()
  form_dict = dict(request.form)
  for key in form_dict:
    if key.endswith('[]'):
      data[key[:-2]] = form_dict[key]
    else:
      data[key] = form_dict[key][0]
  if name is None:
    return data
  return data[name]

class Root(object):

  def __init__(self):
    self.url_map = Map(self.get_url_map(approot))
    #print self.url_map

  def route(self, routes):
    for pattern, endpoint in routes:
      self.url_map.add(Rule(pattern, endpoint=endpoint))

  def get_url_map(self, node):
    rules = []
    attrs = map(lambda attr: getattr(node, attr), filter(lambda attr: not attr.startswith('_'), dir(node)))
    functions = filter(lambda attr: type(attr) is types.FunctionType, attrs)
    if functions:
      attrs = functions
    for attr in attrs:
      if type(attr) is types.ModuleType:
        rules.extend(self.get_url_map(attr))
      elif type(attr) is types.FunctionType:
        arginfo = inspect.getargspec(attr)
        args = arginfo.args
        defaults = arginfo.defaults
        rp = config.root_path if config.root_path.endswith('/') else "%s/" % config.root_path
        np = node.__name__.replace('%s.' % approot.__name__, '').replace('.', '/')
        ap = attr.__name__
        abspath = urlparse.urljoin(urlparse.urljoin(rp, np + '/'), ap + '/')
        args_size = len(args) if args else 0
        defaults_size = len(defaults) if defaults else 0
        for idx in range(args_size-defaults_size, args_size+1):
          args_str = "".join(["<%s>/" % arg for arg in args[:idx]])
          rules.append(Rule(abspath + args_str, endpoint=attr))

        if ap == 'index' or ap == 'default':
          ap = ''
          abspath = urlparse.urljoin(urlparse.urljoin(rp, np + '/'), ap)
          for idx in range(args_size-defaults_size, args_size+1):
            args_str = "".join(["<%s>/" % arg for arg in args[:idx]])
            rules.append(Rule(abspath + args_str, endpoint=attr))
        if np.endswith('index'):
          np = np[:-5]
          abspath = urlparse.urljoin(urlparse.urljoin(rp, np), ap) + ('/' if ap else "")
          for idx in range(args_size-defaults_size, args_size+1):
            args_str = "".join(["<%s>/" % arg for arg in args[:idx]])
            rules.append(Rule(abspath + args_str, endpoint=attr))
    return rules

  def error_404(self):
    html = render_template('404.html')
    response = Response(html, mimetype='text/html')
    response.status_code = 404
    return response

  def dispatch_request(self):
    adapter = self.url_map.bind_to_environ(request.environ)
    try:
      endpoint, values = adapter.match()
      return endpoint(**values)
    except NotFound, e:
      return self.error_404()
    except HTTPException, e:
      if config.use_debugger:
          raise e
      return Response('Sorry! Server is temporary unreachable.', status=500)

  def wsgi_app(self, environ, start_response):
    global request
    request = Request(environ)
    response = self.dispatch_request()
    if isinstance(response, collections.Callable):
      return response(environ, start_response)
    else:
      if config.dict_to_json and isinstance(response, dict):
        import json
        response = json.dumps(response)
      return Response(response, mimetype='text/html')(environ, start_response)

  def run(self, host="127.0.0.1", port=5000, processes=3):
    run_simple(host, 
               port,
               self, 
               use_debugger=config.use_debugger, 
               use_reloader=config.use_reloader, 
               processes=processes)

  def __call__(self, environ, start_response):
    return self.wsgi_app(environ, start_response)


def create_app(with_static=True):
  app = Root()
  if with_static:
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
      '/':  os.getcwd()
    })
  return app

