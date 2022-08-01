from flask import Flask, request, render_template, send_file
import os, datetime, base64

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
            encode(os.path.abspath(p)),
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


def get_path():
    path = request.args.get("path")
    return decode(path), path


def base(path):
    return os.path.basename(path)


app = Flask("FileServer")


@app.route("/")
def home():
    return folder(DIR)


@app.route("/folder")
def folder(folder=""):
    if not folder:
        folder, _ = get_path()

    dirs, files = get_dfs(folder)
    is_root = folder == DIR

    parent = ""
    if is_root:
        index = base(folder)
    else:
        dirname = os.path.dirname(DIR).replace(os.path.sep, "/")
        index = folder.replace(os.path.sep, "/").replace(dirname, "")
        parent = encode(os.path.dirname(folder))

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
    path, _ = get_path()
    return send_file(path)


@app.route("/download")
def download():
    path, _ = get_path()
    if os.path.isdir(path):
        path = ...
        return "downlaod zip"
    return send_file(path, as_attachment=True, attachment_filename=base(path))


app.run(port=7767, debug=1)
