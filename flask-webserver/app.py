#!/usr/bin/env python3

from flask import Flask, redirect, url_for, request, Response, send_from_directory, send_file
from flask_cors import CORS
import os
import time
import re

class SlowResponseMiddleware:
    def __init__(self, app, delay=1, chunk_size=1024):
        self.app = app
        self.delay = delay  # 각 청크 사이의 지연 시간(초)
        self.chunk_size = chunk_size  # 청크 크기(바이트)

    def __call__(self, environ, start_response):
        app_iter = self.app(environ, start_response)
        for chunk in self.chunked_response(app_iter):
            time.sleep(self.delay)  # 지연 시간 추가
            yield chunk

    def chunked_response(self, app_iter):
        for data in app_iter:
            for i in range(0, len(data), self.chunk_size):
                yield data[i:i+self.chunk_size]

app = Flask(__name__)
CORS(app)  # CORS를 애플리케이션에 추가합니다.

# 대역폭 제한 미들웨어 적용
# app.wsgi_app = SlowResponseMiddleware(app.wsgi_app, delay=0.5, chunk_size=1024 * 100)  # 예: 0.5초 지연, 100KB 청크

@app.route('/')
def home():
    return redirect(url_for('pdfs'))

@app.route('/pdfs')
def pdfs():
    base_dir = os.path.abspath(os.path.dirname(__file__))  # 현재 파일의 절대 경로를 가져옵니다.
    files = os.listdir(os.path.join(base_dir, 'static/pdfs'))  # 절대 경로를 사용하여 'static/pdfs' 디렉토리의 파일 목록을 가져옵니다.
    return '<br>'.join(f'<a href="/download/{file}">{file}</a>' for file in files)

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory('static/pdfs', filename, as_attachment=True)

# @app.route('/pdfs/<filename>')
# def pdf_viewer(filename):
#     return send_from_directory('static/pdfs', filename)

# @app.route('/pdfs/<filename>')
# def pdf_viewer(filename):
#     base_dir = os.path.abspath(os.path.dirname(__file__))  # 현재 파일의 절대 경로를 가져옵니다.
#     file_path = os.path.join(base_dir, 'static/pdfs', filename)
#     return send_file(file_path, conditional=True)

@app.route('/pdfs/<filename>')
def download_pdf(filename):
    base_dir = os.path.abspath(os.path.dirname(__file__))  # 현재 파일의 절대 경로를 가져옵니다.
    path = os.path.join(base_dir, 'static/pdfs', filename)
    
    if not os.path.isfile(path):
        return 'File not found', 404

    start, end = 0, None
    range_header = request.headers.get('Range', None)
    
    if range_header:
        range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = int(range_match.group(1))
            if range_match.group(2):
                end = int(range_match.group(2))

    file_size = os.path.getsize(path)
    end = end or file_size - 1

    if start > end or start >= file_size:
        return 'Requested range not satisfiable', 416

    length = end - start + 1

    def generate():
        with open(path, 'rb') as f:
            f.seek(start)
            chunk = f.read(8192)
            while chunk:
                yield chunk
                chunk = f.read(8192)

    headers = {
        'Content-Range': f'bytes {start}-{end}/{file_size}',
        'Accept-Ranges': 'bytes',
        'Content-Length': str(length),
        'Content-Type': 'application/pdf',
    }

    return Response(generate(), status=206, headers=headers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)