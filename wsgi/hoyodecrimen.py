from datetime import datetime
from flask import Blueprint, Flask, jsonify, request, abort, \
    make_response, url_for, send_from_directory,\
    send_file, render_template, g, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text, literal_column, literal
from sqlalchemy import func, and_
from flask_cache import Cache
from flask.ext.assets import Environment, Bundle
from werkzeug.contrib.profiler import ProfilerMiddleware
from functools import wraps
from geoalchemy2.elements import WKTElement
import time
import os
from api.models import db, Cuadrantes, Cuadrantes_Poly
#from redis import Redis
from api.api import API, cache
from flask.ext.compress import Compress
from flask.ext.babel import Babel
from flask.ext.babel import gettext, ngettext
from flask_frozen import Freezer
from htmlmin.main import minify
import functools

_basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 43200 * 20 # 20 days
app.register_blueprint(API)
db = SQLAlchemy(app)
app.config.from_pyfile('apihoyodecrimen.cfg')

cache.init_app(app)
assets = Environment(app)
assets.versions = 'hash'    # use the last modified timestamp
babel = Babel(app)

app.config['FREEZER_STATIC_IGNORE'] = ['/api/v1/*']
freezer = Freezer(app)


def uglify(route_function):
    @functools.wraps(route_function)
    def wrapped(*args, **kwargs):
        yielded_html = route_function(*args, **kwargs)
        minified_html = minify(yielded_html)
        return minified_html

    return wrapped

def add_response_headers(headers={}):
    """This decorator adds the headers passed in to the response"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resp = make_response(f(*args, **kwargs))
            h = resp.headers
            for header, value in headers.items():
                h[header] = value
            return resp
        return decorated_function
    return decorator


def noframes(f):
    """This decorator passes X-Robots-Tag: noindex"""
    @wraps(f)
    @add_response_headers({'X-Frame-Options': 'DENY'})
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


# Simple HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


css_pip_req = Bundle("css/skel.css", "css/style.css",
                     "css/leaflet.css", "css/vendor/metricsgraphics/metricsgraphics.css", "css/crime.css",
                     "css/vendor/leaflet/fullscreen.css",
                     filters="cssmin", output="css/packed-pip-req.%(version)s.css")
assets.register('css_pip_req', css_pip_req)

js_pip_req = Bundle( "js/jquery.1.9.1.min.js",  "js/jquery.dropotron.min.js",
                    "js/skel.min.js",
                    "js/skel-layers.min.js",
                    "js/init.js", "js/vendor/lodash/lodash.min.js", "js/leaflet.js",
                    "js/vendor/leaflet/fullscreen.js", "js/leaflet-pip.js",
                    "js/topojson.v1.min.js", "js/d3.v3.min.js", "js/c3.min.js",
                    "js/vendor/metricsgraphics/metricsgraphics.js",
                    filters='jsmin', output='js/packed-pip-req.%(version)s.js')
assets.register('js_pip_req', js_pip_req)

js_pip = Bundle("js/pip.js", filters='jsmin', output="js/packed-pip.%(version)s.js")
assets.register("js_pip", js_pip)

css_maps_req = Bundle("css/skel.css", "css/style.css",
                      "css/leaflet.css", "css/crime.css",  "css/vendor/metricsgraphics/metricsgraphics.css",
                      filters="cssmin", output="css/packed-maps-reqs.%(version)s.css", )
assets.register('css_maps_req', css_maps_req)

js_maps_req = Bundle("js/jquery.min.js", "js/jquery.dropotron.min.js",
                     "js/skel.min.js", "js/skel-layers.min.js", "js/init.js",
                     "js/d3.v3.min.js",
                     "js/topojson.v1.min.js", "js/d3.tip.v0.6.3.js",
                     "js/tooltip.js", "js/vendor/lodash/lodash.min.js", "js/vendor/metricsgraphics/metricsgraphics.js",
                     filters="jsmin", output="js/packed-maps-reqs.%(version)s.js")
assets.register('js_maps_req', js_maps_req)

js_maps = Bundle("js/maps.js", filters='jsmin', output="js/packed-maps.js")
assets.register('js_maps', js_maps)

js_leaflet = Bundle("js/leaflet-map.js", filters='jsmin', output="js/packed-leaflet-map.js")
assets.register('js_leaflet', js_maps)

css_leaflet_req = Bundle("css/l.geosearch.css", "css/leaflet.css", "css/L.Control.Locate.css",
                         filters="cssmin", output="css/packed-leaflet-req.%(version)s.css")
assets.register('css_leaflet_req', css_leaflet_req)

js_leaflet_req = Bundle("js/cuadrantes_neighbors.json","js/leaflet.js", "js/L.Control.Locate.js",
                        "js/leaflet-hash.js", "js/jquery.1.8.3.min.js",
                        "js/topojson.v1.min.js",
                        "js/topojson.v1.min.js", "js/l.control.geosearch.js",
                        "js/vendor/leaflet/bing.js",
                        "js/l.geosearch.provider.google.js",
                        "js/d3.v3.min.js", "js/colorbrewer.js",
                        "js/underscore-min.js",
                        "js/vendor/metricsgraphics/metricsgraphics.js",
                        filters="jsmin", output="js/packed-leaflet.%(version)s.js")
assets.register('js_leaflet_req', js_leaflet_req)

latlong_css = Bundle("css/vendor/carto/cartodb.css",
                         filters="cssmin", output="css/packed-latlong.css")
assets.register('css_latlong_css', latlong_css)

latlong_js = Bundle("js/vendor/carto/cartodb.js",
                    filters="jsmin", output="js/packed-latlong.%(version)s.js", )
assets.register('js_latlong_js', latlong_js)

latlong_bootstrap_css = Bundle("css/vendor/bootstrap/bootstrap.min.css",
                              "css/vendor/bootstrap/bootstrap-select.min.css",
                              "css/vendor/bootstrap/cartodb.css",
                              "css/font-awesome.min.css",
                              "css/vendor/bootstrap/nouislider.css",
                    filters="cssmin", output="css/packed-latlong-bootstap.%(version)s.css", )
assets.register('latlong_bootstrap_css', latlong_bootstrap_css)

latlong_bootstrap_js = Bundle("js/vendor/bootstrap/jquery-3.1.1.js",
                              "js/vendor/bootstrap/bootstrap.min.js",
                              "js/vendor/bootstrap/bootstrap-select.min.js",
                              "js/vendor/bootstrap/nouislider.min.js",
                    filters="jsmin", output="js/packed-latlong-bootstap.%(version)s.js", )
assets.register('latlong_bootstrap_js', latlong_bootstrap_js)

@babel.localeselector
def get_locale():
    return getattr(g, 'lang')


@app.route('/robots.txt')
def robots():
    return send_from_directory(os.path.join(_basedir, 'static'), 'robots.txt')

@app.route('/test-cache')
@cache.cached()
def test_cache():
    import random
    return str(random.random())

@cache.cached()
@app.route('/en/')
def api_home_html():
    setattr(g, 'lang', 'en')
    return render_template('pip.html')

@cache.cached()
@app.route('/')
def api_home_html_es():
    setattr(g, 'lang', 'es')
    return render_template('pip.html')

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(os.path.join(_basedir, 'static'), 'sitemap.xml')


@app.route('/api/')
def api_index_html():
    return send_from_directory(os.path.join(_basedir, 'static', 'sphinx', 'html'), 'index.html')


@app.route('/api/<path:filename>')
def api_html(filename):
    if filename.endswith('/'):
         filename += 'index.html'
    return send_from_directory(os.path.join(_basedir, 'static', 'sphinx', 'html'), filename)


@app.route('/static/<path:filename>')
def static_html(filename):
    if filename.endswith('/'):
         filename += 'index.html'
    return send_from_directory(os.path.join(_basedir, 'static'), filename)

@app.route('/en/rates')
@cache.cached()
def rates():
    setattr(g, 'lang', 'en')
    return render_template('rates-sectores.html')

@app.route('/tasas')
@cache.cached()
def tasas():
    setattr(g, 'lang', 'es')
    return render_template('rates-sectores.html')


@app.route('/en/trends')
@cache.cached()
def change():
    setattr(g, 'lang', 'en')
    return render_template('change-cuadrantes.html')


@app.route('/tendencias')
@cache.cached()
def tendencias():
    setattr(g, 'lang', 'es')
    return render_template('change-cuadrantes.html')

@app.route('/en/counts')
@cache.cached()
def counts():
    setattr(g, 'lang', 'en')
    return render_template('counts-cuadrantes.html')


@app.route('/numero')
@cache.cached()
def numero():
    setattr(g, 'lang', 'es')
    return render_template('counts-cuadrantes.html')


@app.route('/en/map')
@cache.cached()
def mapa():
    setattr(g, 'lang', 'en')
    return render_template('latlong_map_boot.html')


@app.route('/mapa')
@cache.cached()
def mapa_es():
    setattr(g, 'lang', 'es')
    return render_template('latlong_map_boot.html')

@app.route('/mapa-google-temp-no-usar')
@cache.cached()
def mapa_es_google():
    setattr(g, 'lang', 'es')
    return render_template('latlong_map_boot.html')


@app.route('/en/crime')
@cache.cached()
def crime():
    setattr(g, 'lang', 'en')
    return render_template('crime.html')


@app.route('/crimen')
@cache.cached()
def crime_es():
    setattr(g, 'lang', 'es')
    return render_template('crime.html')



@app.route('/en/charts')
@cache.cached()
def charts():
    setattr(g, 'lang', 'en')
    return render_template('charts.html')


@app.route('/charts')
@cache.cached()
def charts_es():
    setattr(g, 'lang', 'es')
    return render_template('charts.html')

@app.route('/en/hours')
@cache.cached()
def hours():
    setattr(g, 'lang', 'en')
    return render_template('hours.html')


@app.route('/hora')
@cache.cached()
def hours_es():
    setattr(g, 'lang', 'es')
    return render_template('hours.html')


@app.route('/en/days')
@cache.cached()
def days():
    setattr(g, 'lang', 'en')
    return render_template('days.html')


@app.route('/dia')
@cache.cached()
def days_es():
    setattr(g, 'lang', 'es')
    return render_template('days.html')


@app.route('/en/about')
@cache.cached()
def about():
    setattr(g, 'lang', 'en')
    return render_template('about.html')


@app.route('/acerca')
@cache.cached()
def about_es():
    setattr(g, 'lang', 'es')
    return render_template('about.html')


@app.route('/en/sectores-map')
@cache.cached()
def sectores_map():
    setattr(g, 'lang', 'en')
    return render_template('sectores-map.html')


@app.route('/sectores-mapa')
@cache.cached()
def sectores_map_es():
    setattr(g, 'lang', 'es')
    return render_template('sectores-map.html')

@app.route('/en/cuadrantes-map')
@cache.cached()
def cuadrantes_map():
    setattr(g, 'lang', 'en')
    return render_template('cuadrantes-map.html')

@app.route('/cuadrantes-mapa')
@cache.cached()
def cuadrantes_mapa():
    setattr(g, 'lang', 'es')
    return render_template('cuadrantes-map.html')


# Google webmaster verification
@app.route('/google055ef027e7764e4d.html')
def google055ef027e7764e4d():
    return 'google-site-verification: google055ef027e7764e4d.html'

# Blitz verification
@app.route('/mu-01188fe9-0b813050-b0f51076-c96f41fb.txt')
def mu01188fe9():
    return '42', 200,  {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/api/_static/<path:filename>')
def static__api(filename):
    return send_from_directory(os.path.join(_basedir, 'static',
                                            'sphinx', 'html', '_static'),
                               filename)


@app.route('/css/<path:filename>')
def static_css(filename):
    return send_from_directory(os.path.join(_basedir, 'static', 'css'), filename)


@app.route('/font/<path:filename>')
def static_font(filename):
    return send_from_directory(os.path.join(_basedir, 'static','font'), filename)

@app.route('/fonts/<path:filename>')
def static_fonts(filename):
    return send_from_directory(os.path.join(_basedir, 'static','fonts'), filename)


@app.route('/js/<path:filename>')
def static_js(filename):
    return send_from_directory(os.path.join(_basedir, 'static','js'), filename)


@app.route('/images/<path:filename>')
def static_images(filename):
    return send_from_directory(os.path.join(_basedir, 'static','images'),
                               filename)

@app.route('/favicon.ico')
def static_images_favicon():
    return send_from_directory(os.path.join(_basedir, 'static','images'),
                               'favicon.ico')

@app.route('/favicon-<string:size>')
def static_favicon_slash(size):
    return send_from_directory(os.path.join(_basedir, 'static','images'),
                               'favicon-' + size)

@app.route('/apple-touch-icon-<string:size>')
def static_apple(size):
    return send_from_directory(os.path.join(_basedir, 'static','images'),
                               'apple-touch-icon-' + size)

@app.route('/android-icon-<string:size>')
def static_android(size):
    return send_from_directory(os.path.join(_basedir, 'static','images'),
                               'android-icon-' + size)

@app.route('/ms-icon-<string:size>')
def static_msicon(size):
    return send_from_directory(os.path.join(_basedir, 'static','images'),
                               'ms-icon-' + size)

@app.route('/manifest.json')
def static_manifest():
    return send_from_directory(os.path.join(_basedir, 'static','images'),
                               'manifest.json')

@app.route('/browserconfig.xml')
def static_browserconfig():
    return send_from_directory(os.path.join(_basedir, 'static','images'),
                               'browserconfig.xml')


if __name__ == '__main__':
    with app.app_context():
        cache.clear()

    db.create_all()

    debug = False
    # Running locally
    if 'OPENSHIFT_APP_UUID' not in os.environ:
        app.config['PROFILE'] = True
        app.config['ASSETS_DEBUG'] = True
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
        debug = True
        #render_template = uglify(render_template)
    else:
        render_template = uglify(render_template)

    #freezer.freeze()
    app.run(debug=debug)
