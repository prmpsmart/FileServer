# MIT License

# Copyright (c) 2022 Apata Miracle Peter

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from flask import Flask, request, render_template, send_file
import os, datetime, base64, random

DIR = os.getcwd()
BYTE = 1024
UNITS = [
    "B",
    "KB",
    "MB",
    "GB",
    "TB",
]


def get_size(file: str) -> str:
    size = os.path.getsize(file)
    order = 0
    while size >= BYTE and order < len(UNITS):
        order += 1
        size /= BYTE
    return f"{size:.1f} {UNITS[order]}"


def get_dfs(folder: str) -> str:
    dirs = []
    files = []

    for df in os.listdir(folder):
        p = os.path.join(folder, df)

        ls = [
            f"?path={encode(os.path.abspath(p))}&rand={random.randint(0, 2000)}",
            df,
            get_size(p),
            datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime(
                "%d/%m/%Y %I:%M:%S %p"
            ),
        ]
        master = None
        if os.path.isdir(p):
            master = dirs
        elif os.path.isfile(p):
            master = files

        if master != None:
            master.append(ls)

    dirs.sort()
    files.sort()
    return dirs, files


def encode(path: str):
    return base64.b64encode(path.encode()).decode()


def decode(path: str):
    return base64.b64decode(path.encode()).decode()


def get_request_path():
    path = request.args.get("path")
    return escape(decode(path)), path


def base(path):
    return os.path.basename(path)


def escape(path: str):
    return path.replace(os.path.sep, "/")


app = Flask("FileServer")


@app.route("/")
def home():
    return folder(DIR)


@app.route("/folder")
def folder(folder=""):
    if not folder:
        folder, _ = get_request_path()

    dirs, files = get_dfs(folder)
    is_root = folder == DIR

    parent = ""
    if is_root:
        index = base(folder)
    else:
        dirname = os.path.dirname(DIR).replace(os.path.sep, "/")
        index = folder.replace(os.path.sep, "/").replace(dirname, "")
        parent = (
            f"?path={encode(os.path.dirname(folder))}&rand={random.randint(0, 2000)}"
        )

    return render_template(
        "file_server.html",
        dirs=dirs,
        files=files,
        is_root=is_root,
        parent=parent,
        index=index,
    )


@app.route("/file")
def file():
    file, _ = get_request_path()
    if escape(DIR) not in file:
        return "Path not found!"
    return send_file(file)


@app.route("/download")
def download():
    path, _ = get_request_path()
    if os.path.isdir(path):
        path = ...
        return "downlaod zip"
    return send_file(path, as_attachment=True, attachment_filename=base(path))


app.run(port=7767, debug=1)
