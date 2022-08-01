import socket, os

IP = lambda: socket.gethostbyname(socket.gethostname())
print(IP())

for root, dirs, files in os.walk("../"):
    for file in files:
        if "pyc" in os.path.split(file)[1]:
            continue
    if os.path.basename(root) == "__pycache__":
        print(root)
    else:
        print(root, 34)
