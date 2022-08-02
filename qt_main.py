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


from PySide6.QtGui import *
from PySide6.QtCore import *
from PySide6.QtWidgets import *
import PySide6.QtNetwork, socket, resources, os, zipfile, datetime, random, base64
from werkzeug.serving import make_server, BaseWSGIServer
from flask import Flask, send_file, request, render_template

TITLE = "File Server"


class QSwitch(QAbstractButton):
    def __init__(
        self,
        parent=None,
        track_radius=10,
        thumb_radius=8,
        thumb_offset=4,
        useOffset=True,
        text_margin=4,
    ):
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.text_margin = text_margin
        self._track_radius = track_radius
        self._thumb_radius = thumb_radius
        self._thumb_offset = thumb_offset
        self._useOffset = useOffset
        self._offset = self._thumb_offset

        palette = self.palette()
        if self._thumb_radius > self._track_radius:
            self._track_color = {
                True: palette.highlight(),
                False: palette.dark(),
            }
            self._thumb_color = {
                True: palette.highlight(),
                False: palette.light(),
            }
            self._text_color = {
                True: palette.highlightedText().color(),
                False: palette.dark().color(),
            }
            self._thumb_text = {
                True: "",
                False: "",
            }
            self._track_opacity = 0.5
        else:
            self._thumb_color = {
                True: palette.highlightedText(),
                False: palette.light(),
            }
            self._track_color = {
                True: palette.highlight(),
                False: palette.dark(),
            }
            self._text_color = {
                True: palette.highlight().color(),
                False: palette.dark().color(),
            }
            self._thumb_text = {
                True: "✔",
                False: "✕",
            }
            self._thumb_text = {
                True: "1",
                False: "0",
            }
            self._track_opacity = 1

    @Property(int)
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        self._offset = value
        self.update()

    @property
    def thumb_radius(self):
        if self._useOffset:
            return self.height() - self._thumb_offset * 2
        else:
            return self._thumb_radius

    @property
    def thumb_y_offset(self):
        if self._useOffset:
            return self._thumb_offset
        else:
            return (self.height() - self._thumb_radius) / 2

    @property
    def next_offset(self):
        if self.isChecked():
            return self.width() - self.thumb_radius - self.thumb_x_offset
        else:
            return self.thumb_x_offset

    @property
    def thumb_x_offset(self):
        if self._useOffset:
            return self._thumb_offset
        else:
            return (self.height() - self._thumb_radius) / 2

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):  # pylint: disable=invalid-name, unused-argument
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        track_opacity = self._track_opacity
        thumb_opacity = 1.0
        text_opacity = 1.0

        if self.isEnabled():
            track_brush = self._track_color[self.isChecked()]
            thumb_brush = self._thumb_color[self.isChecked()]
            text_color = self._text_color[self.isChecked()]
        else:
            track_opacity *= 0.8
            track_brush = self.palette().shadow()
            thumb_brush = self.palette().mid()
            text_color = self.palette().shadow().color()

        # drawing the track
        p.setBrush(track_brush)
        p.setOpacity(track_opacity)
        p.drawRoundedRect(
            0,
            0,
            self.width(),
            self.height(),
            self._track_radius,
            self._track_radius,
        )

        # drawing the thumb
        p.setBrush(thumb_brush)
        p.setOpacity(thumb_opacity)
        p.drawEllipse(
            self.offset,
            self.thumb_y_offset,
            self.thumb_radius,
            self.thumb_radius,
        )

        # drawing the thumb
        p.setPen(text_color)
        p.setOpacity(text_opacity)
        font = p.font()
        font.setPixelSize(int(0.8 * self.thumb_radius))
        p.setFont(font)
        p.drawText(
            QRectF(
                self.offset,
                self.thumb_y_offset,
                self.thumb_radius,
                self.thumb_radius,
            ),
            Qt.AlignCenter,
            self._thumb_text[self.isChecked()],
        )

    def mouseReleaseEvent(self, event):  # pylint: disable=invalid-name
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            anim = QPropertyAnimation(self, b"offset", self)
            anim.setDuration(120)
            anim.setStartValue(self.offset)
            anim.setEndValue(self.next_offset)
            anim.start()

    def enterEvent(self, event):  # pylint: disable=invalid-name
        self.setCursor(Qt.PointingHandCursor)
        super().enterEvent(event)


class QToggle(QSwitch):
    ...


class Thread(QThread):
    def __init__(self, run) -> None:
        super().__init__()
        self._run = run

    def run(self):
        self._run()


class Label(QLabel):
    ...


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


class Window(Server, QWidget):
    def __init__(self):
        QWidget.__init__(self)
        Server.__init__(self)

        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setWindowTitle(TITLE)

        self.flask_app.add_url_rule("/download", view_func=self.download)
        self.flask_app.add_url_rule("/served", view_func=self.served)

        self._port: int = 7767
        self.count = 0

        self._server: BaseWSGIServer = None

        lay = QVBoxLayout(self)

        form = QFormLayout()
        form.setFormAlignment(Qt.AlignCenter)
        lay.addLayout(form)

        l = QHBoxLayout()
        self.server_ip = Label()
        self.server_ip.setMaximumWidth(100)
        l.addWidget(self.server_ip)
        l.addStretch()
        self.counter = Label(f"{self.count} Downloads")
        self.counter.setAlignment(Qt.AlignCenter)
        self.counter.setMaximumWidth(100)
        l.addWidget(self.counter)
        form.addRow(Label("Server IP : "), l)
        self.ip_timer = self.startTimer(1000)

        l = QHBoxLayout()
        self.server_port = QLineEdit()
        self.server_port.setValidator(QIntValidator())
        self.server_port.setMaximumWidth(100)
        l.addWidget(self.server_port)
        l.addStretch()
        self.url = Label()
        self.url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        l.addWidget(self.url)
        form.addRow(Label("Server PORT : "), l)

        self.isFolder = QSwitch()
        self.isFolder.toggled.connect(self.switch_icon)
        form.addRow(Label("Path is Folder ? "), self.isFolder)

        l = QHBoxLayout()
        self.path = Label()
        self.path.setMinimumWidth(300)
        l.addWidget(self.path)
        self.icons = [QIcon("static/file"), QIcon("static/folder")]
        self.icon_texts = ["Browse File", "Browse Folder"]
        self.browse_btn = QPushButton(self.icons[0], self.icon_texts[0])
        self.browse_btn.clicked.connect(self.browse)
        l.addWidget(self.browse_btn)
        form.addRow(Label("Path to Serve : "), l)

        self.serve = QSwitch()
        self.serve.clicked.connect(self.server)
        form.addRow(Label("Serve ? "), self.serve)

        self._thread_ = None

        # self.t = QTimer()
        # self.t.singleShot(200, lambda: self.isFolder.setChecked(True))

        self.show()

    def timerEvent(self, event: QTimerEvent):
        timerId = event.timerId()
        if timerId == self.ip_timer:
            self.server_ip.setText(self.ip)

    @property
    def datetime(self) -> str:
        return datetime.datetime.now().strftime("%A %d/%m/%Y %I/%M/%S %p")

    def home(self):
        if os.path.isfile(self._path):
            path = os.path.basename(self._path)
            return f"""
                <p>Home Page @ {self.datetime}</p>
                <p><a href=served?dum{random.randint(1, 2000)}>Download {path}</a></p>
                <p><a href=served?latest={random.randint(1, 2000)}>Download Latest {path}</a></p>
                """
        return super().home()

    def download(self):
        path, _ = self.get_request_path()
        if os.path.isdir(path):
            path = self.zip(path, True)

        self.count += 1
        self.counter.setText(f"{self.count} Downloads")
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
        if self.serve.isChecked():
            if self._path:
                self._port = int(self.server_port.text() or self._port)
                self.server_port.setText(str(self._port))
                self.url.setText(f"http://{self.ip}:{self._port}")
                self.server_port.setDisabled(True)

                self._server = make_server(self.ip, self._port, self.flask_app)

                self.ctx = self.flask_app.app_context()
                self.ctx.push()

                self._thread_ = Thread(self.serve_forever)
                self._thread_.start()

            else:
                QMessageBox.critical(
                    self, "No path to serve", "Select a path to serve first!"
                )
                self.serve.setChecked(False)

        else:
            if self._server:
                self._server.shutdown_signal = True
                self.server_port.setEnabled(True)
                self._server = None

    def serve_forever(self):
        self._server.serve_forever()

    def switch_icon(self, toggled):
        self.browse_btn.setIcon(self.icons[toggled])
        self.browse_btn.setText(self.icon_texts[toggled])

    def browse(self):
        path = ""
        if self.isFolder.isChecked():
            path = QFileDialog.getExistingDirectory(
                self, "Select a folder to zip and serve?"
            )
        else:
            path = QFileDialog.getOpenFileName(self, "Select a file serve?")
        if path:

            self.count = 0
            if isinstance(path, tuple):
                path = path[0]

            self._path = path
            self.path.setText(os.path.basename(path))
            self.path.setToolTip(path)

    @property
    def ip(self):
        ip_, localhost = None, None
        for ip in PySide6.QtNetwork.QNetworkInterface().allAddresses():
            if ip.protocol() == ip.IPv4Protocol:
                _ip = ip.toString()
                if ip.isLoopback():
                    localhost = _ip
                else:
                    ip_ = _ip
        return ip_ or localhost

    @property
    def _ip(self):
        return socket.gethostbyname(socket.gethostname())

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


class App(QApplication):
    def close_win(self):
        if self.win._server:
            self.win._server.shutdown_signal = True
        self.quit()

    def __init__(self):
        super().__init__()

        self.win = Window()
        self.win.destroyed.connect(self.close_win)

        self.setStyleSheet(
            """
         QWidget {
            font-family: Times New Roman;
         }
        QLineEdit, QLabel {
            padding: 4px;
            padding-top: 2px;
            padding-bottom: 2px;
            border: 0px outset white;
            border-radius: 10px;
            background-color: #27384b;
            color: #fafafa;
            font-size: 16px;
            min-height: 1.5em;
        }
        Label {
            min-width: 6.5em;
        }
        QLineEdit:hover {
            border: 1px solid #1d87c5;
            color: #fafafa;
        }
        QLineEdit:focus {
            border: 1px solid #166594;
        }
        QLineEdit:selected {
            background-color: #1d87c5;
            color: #17222d; 
        }
        QPushButton {
            border-style: outset;
            border-width: 2px;
            border-radius: 10px;
            border-color: black;
            font: bold 14px;
            padding: 2px;
            min-height: 1.5em;
            max-width: 7.5em;
        }
        QPushButton:hover {
            background-color: red;
            color: white;
        }
        QPushButton:pressed, QPushButton:checked {
            background-color: green;
            color: white;
        }
        QSwitch {
            min-width: 5em;
            min-height: 2em;
        }
        """
        )


app = App()
app.exec()
