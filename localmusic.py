from flask import Flask
from flask import render_template
from flask import jsonify
from flask import request
from flask import send_file
from flask import make_response
import catalog
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rebuild')
def rebuild():
    catalog.rebuild()
    return jsonify(result='OK')
    
@app.route('/inventory.json')
def inventory():
    results = catalog.search('')
    grouped = catalog.group_results(results, levels_deep=0)
    return jsonify(result=grouped)

@app.route('/search.json')
def search_catalog():
    try:
        query = request.args.get('q', '')
        results = list(catalog.search(query))
    except:
        results = []
    return jsonify(result=results)

@app.route('/download/<int:id>.mp3')
def download_song(id):
    id, full_path = catalog.get_by_id(id)
    
    filesize = os.path.getsize(full_path)
    start = 0
    stop = filesize - 1
    length = stop - start + 1
    
    status = '200 OK'
    headers = {
        'Accept-Ranges': 'bytes',
        'Content-Type': 'audio/mpeg',
        'Content-Length': filesize,
        'Content-Range': 'bytes %s-%s/%s' % (start, stop, filesize),
        'Cache-Control': 'must-revalidate, post-check=0, pre-check=0',
        'Pragma': 'public',
    }
    http_range = request.headers.get('Range', None)
    if http_range:
        _, range = http_range.split('=')
        start, stop = range.split('-')
        start = start or 0
        stop = stop or filesize - 1
        start = int(start)
        stop = int(stop)
        stop = min(stop, filesize - 1)
        length = stop - start + 1
        if start > stop:
            # HTTP/1.1 416 Requested Range Not Satisfiable
            status = 416
            headers.update({
                'Content-Length': '0',
                'Content-Range': 'bytes */0'
            })
            return make_response('', status, headers)
        else:
            # HTTP/1.1 206 Partial Content
            status = 206
            headers.update({
                'Content-Length': length,
                'Content-Range': 'bytes %s-%s/%s' % (start, stop, length)
            })
    
    with open(full_path) as f:
        f.seek(start)
        bytes = f.read(length)

    return make_response(bytes, status, headers)

if __name__ == "__main__":
    app.debug = True
    app.run()