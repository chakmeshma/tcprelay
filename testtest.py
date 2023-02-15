import sys
import socket
import threading
import time

NET_MSG_SIZE = 4096

running = 1


def createNewListenSocket(hostname, port):
    s = None

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((hostname, port))
        s.listen(1)
    except:
        if s:
            s.close()
            print("Could not open socket")
            sys.exit(1)

    return s


def handleEchoServer(relayacceptedsocket: socket.socket):
    global running

    relayacceptedsocket.setblocking(False)

    theerrors = set()
    lastErrosSize = 0

    ccc1 = socket.EAGAIN
    ccc2 = socket.EWOULDBLOCK
    ccc3 = socket.EBADF

    while running:
        try:
            tunnel_data = relayacceptedsocket.recv(NET_MSG_SIZE)
            bdata = bytes(1024 * 1024 * 1024 * 3)
            relayacceptedsocket.sendall(bdata)
        except socket.error as e:
            theerrors.add(e.errno)

            if len(theerrors) != lastErrosSize:
                print(theerrors)
                lastErrosSize = len(theerrors)

    relayacceptedsocket.close()


def createRelayServer(relayhost, relayport):
    global running

    relaysocket = createNewListenSocket(relayhost, relayport)

    relayacceptedsocket, echoaddr = relaysocket.accept()

    relay_thread = threading.Thread(target=handleEchoServer, args=(relayacceptedsocket,))
    relay_thread.start()

    # while running:
    #     import time
    #     time.sleep(1.0)


createRelayServer('0.0.0.0', 1666)
