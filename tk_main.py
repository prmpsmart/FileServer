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

from signal import Signals
from threading import Thread
from tkinter import *
from tkinter import ttk, messagebox, filedialog
import socket, os, zipfile, datetime, random, base64
from werkzeug.serving import make_server, BaseWSGIServer
from flask import Flask, send_file, request, render_template


BG = "#27384b"
FG = "white"
TITLE = "File Server"


class Check(Checkbutton):
    def __init__(self, *args, **kwargs):
        self.var = BooleanVar()
        super().__init__(*args, variable=self.var, **kwargs, anchor="w")

    @property
    def checked(self):
        return bool(self.var.get())

    def set(self, value: bool):
        self.var.set(value)


class Label_(Label):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, bg=BG, fg=FG, anchor="w")


class LabelL(Frame):
    def __init__(self, master, text, w):
        super().__init__(master)

        _w = 90
        label = Label_(self, text=text)
        label.place(relx=0, rely=0, relh=1, w=_w)

        s = 5
        self.label = Label_(self)
        self.label.place(x=_w + s, rely=0, relh=1, w=w - _w - s)

    def setText(self, text: str):
        self.label.config(text=text)

    def text(self):
        return self.label["text"]


class LabelE(Frame):
    def __init__(self, master, text, w):
        super().__init__(master)

        _w = 90
        label = Label_(self, text=text)
        label.place(relx=0, rely=0, relh=1, w=_w)

        s = 5
        self.entry = Entry(self, bg=BG, fg=FG)
        self.entry.place(x=_w + s, rely=0, relh=1, relw=w - _w - s)

    def text(self):
        return self.entry.get()

    def setText(self, text: str):
        self.entry.delete("0", "end")
        self.entry.insert("0", text)


class Server:
    def get_size(self, file: str) -> str:
        size = os.path.getsize(file)
        order = 0
        while size >= self.BYTE and order < len(self.UNITS):
            order += 1
            size /= self.BYTE
        return f"{size:.1f} {self.UNITS[order]}"

    def get_dfs(self, folder: str) -> str:
        dirs = []
        files = []

        for df in os.listdir(folder):
            p = os.path.join(folder, df)

            ls = [
                f"?path={self.encode(os.path.abspath(p))}&rand={random.randint(0, 2000)}",
                df,
                self.get_size(p),
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

    def encode(self, path: str):
        return base64.b64encode(path.encode()).decode()

    def decode(self, path: str):
        return base64.b64decode(path.encode()).decode()

    def get_request_path(self):
        path = request.args.get("path")
        return self.escape(self.decode(path)), path

    def base(self, path):
        return os.path.basename(path)

    def __init__(self):
        self.BYTE = 1024
        self.UNITS = [
            "B",
            "KB",
            "MB",
            "GB",
            "TB",
        ]
        self._path: str = ""

        self.flask_app = Flask(TITLE)
        self.flask_app.add_url_rule("/", view_func=self.home)
        self.flask_app.add_url_rule("/folder", view_func=self.folder)
        self.flask_app.add_url_rule("/file", view_func=self.file)

    def home(self):
        return self.folder(self._path)

    def folder(self, folder=""):
        dirname = self.escape(os.path.dirname(self._path))

        if not folder:
            folder, _ = self.get_request_path()
            if self.escape(self._path) not in folder:
                return "Path not found!"

        dirs, files = self.get_dfs(folder)
        is_root = folder == self._path

        parent = ""
        current = f"?path={self.encode(folder)}&rand={random.randint(0, 2000)}"
        if is_root:
            index = self.base(folder)
        else:
            index = self.escape(folder).replace(dirname, "")
            parent = f"?path={self.encode(os.path.dirname(folder))}&rand={random.randint(0, 2000)}"

        return render_template(
            "file_server.html",
            dirs=dirs,
            files=files,
            is_root=is_root,
            parent=parent,
            current=current,
            index=index,
        )

    def file(self):
        file, _ = self.get_request_path()
        if self.escape(self._path) not in file:
            return "Path not found!"
        return send_file(file)

    def escape(self, path: str):
        return path.replace(os.path.sep, "/")


class App(Server, Tk):
    def close_server(self):
        self.destroy()
        s = os.getpid()
        os.kill(s, Signals.SIGTERM)

    def __init__(self) -> None:
        Server.__init__(self)
        Tk.__init__(self)

        width = 503
        self.geometry(f"{width}x190")
        self.title(TITLE)

        self.protocol("WM_DELETE_WINDOW", self.close_server)
        self.resizable(0, 0)

        self.flask_app.add_url_rule("/download", view_func=self.download)
        self.flask_app.add_url_rule("/served", view_func=self.served)

        self._port: int = 7767
        self.count = 0

        self._server: BaseWSGIServer = None

        self.w = 0
        self.y = 0.02
        h = 0.18

        def place(wid, width):
            wid.place(relx=0.02, rely=self.y, relh=h, w=width)
            self.y += h + 0.02

        def place2(wid, w=0):
            wid.place(x=width - (w or 105), rely=self.y, relh=h, w=w or 100)

        w = 220
        self.counter = Label_(self, text=f"{self.count} Downloads")
        place2(self.counter)

        self.server_ip = LabelL(self, "Server IP : ", w)
        place(self.server_ip, w)

        self.url = Entry(self, bg=BG, fg=FG)
        place2(self.url, 180)

        self.server_port = LabelE(self, "Server PORT : ", w)
        place(self.server_port, w)

        self.icon_texts = ["Browse File", "Browse Folder"]
        self.isFolder = Check(self, text="Path is Folder ? ", command=self.switch_icon)
        place(self.isFolder, 150)

        self.browse_btn = Button(
            self,
            bg=BG,
            fg=FG,
            relief="groove",
            text=self.icon_texts[0],
            command=self.browse,
        )
        place2(self.browse_btn)

        w = width - 120
        self.path = LabelL(self, "Path to Serve : ", w)
        place(self.path, w)

        self.serve = Check(self, text="Serve ? ", command=self.server)
        place(self.serve, 150)

        self.after(500, self.set_ip)

        self.mainloop()

    @property
    def ip(self):
        return socket.gethostbyname(socket.gethostname())

    def set_ip(self):
        self.server_ip.setText(self.ip)
        self.after(500, self.set_ip)

    def switch_icon(self):
        toggled = self.isFolder.checked
        self.browse_btn.config(text=self.icon_texts[toggled])

    def download(self):
        path, _ = self.get_request_path()
        if os.path.isdir(path):
            path = self.zip(path, True)

        self.count += 1
        self.counter.config(text=f"{self.count} Downloads")
        return send_file(path, as_attachment=True, attachment_filename=self.base(path))

    def served(self):
        latest = request.args.get("latest", 0, bool)
        path = self._path

        if os.path.isdir(self._path):
            path = self.zip(self._path, latest)

        if path:
            basename = os.path.basename(path)
            self.count += 1
            self.counter.setText(f"{self.count} Downloads")
            return send_file(path, attachment_filename=basename, as_attachment=True)
        return "No file is served"

    def server(self):
        if self.serve.checked:
            if self._path:
                self._port = int(self.server_port.text() or self._port)
                self.server_port.setText(str(self._port))

                self.url.delete("0", "end")
                self.url.insert("0", f"http://{self.ip}:{self._port}")

                self.server_port.entry.config(state="disabled")

                self._server = make_server(self.ip, self._port, self.flask_app)

                self.ctx = self.flask_app.app_context()
                self.ctx.push()

                self._thread_ = Thread(target=self.serve_forever)
                self._thread_.start()

            else:
                messagebox.showwarning(
                    "No path to serve", "Select a path to serve first!"
                )
                self.serve.set(False)

        else:
            if self._server:
                self._server.shutdown_signal = True
                self.server_port.entry.config(state="normal")
                self._server = None

    def serve_forever(self):
        self._server.serve_forever()

    def browse(self):
        path = ""
        if self.isFolder.checked:
            path = filedialog.askdirectory(
                parent=self, mustexist=True, title="Select a folder to zip and serve?"
            )
        else:
            path = filedialog.askopenfilename(parent=self, title="Select a file serve?")
        if path:

            self.count = 0
            if isinstance(path, tuple):
                path = path[0]

            self._path = path
            self.path.setText(os.path.basename(path))

    def zip(self, folder: str, latest=False) -> str:
        zipFileName = folder + ".zip"
        if os.path.isfile(zipFileName) and not latest:
            return zipFileName
        print(f"Zipping {folder}")

        # Create zip file
        with zipfile.ZipFile(
            zipFileName, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zipFile:
            if os.path.isdir(folder):
                for root, dirs, files in os.walk(folder):
                    if os.path.basename(root) == "__pycache__":
                        continue

                    for file in files:
                        filename = os.path.join(root, file)
                        arc = root.replace(folder, os.path.basename(folder))
                        arcname = os.path.join(arc, file)
                        zipFile.write(filename, arcname, zipfile.ZIP_DEFLATED)
            else:
                zipFile.write(folder, zipFileName, zipfile.ZIP_DEFLATED)
        return zipFileName


App()
