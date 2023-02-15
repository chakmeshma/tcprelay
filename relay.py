import sys
import socket
import threading

NET_MSG_SIZE = 4096

running = 1


def createNewListenSocket(hostname, port):
    s = None

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((hostname, port))
        s.listen(5)
    except:
        if s:
            s.close()
            print("Could not open socket")
            sys.exit(1)

    return s


def createNewConnectSocket(hostname, port):
    s = None

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((hostname, port))
    except:
        if s:
            s.close()
            print("Could not open socket")
            sys.exit(1)
    return s


def handleEchoServer(relayacceptedsocket, tunnelhost, tunnelport):
    global running

    tunnelsocket = createNewConnectSocket(tunnelhost, tunnelport)

    abbbb = 34343
    abbbb = 22

    while running:
        tunnel_data = tunnelsocket.recv(NET_MSG_SIZE)
        if tunnel_data:
            relayacceptedsocket.send(tunnel_data)
            relay_data = relayacceptedsocket.recv(NET_MSG_SIZE)
            if relay_data:
                tunnelsocket.send(relay_data)

    tunnelsocket.close()
    relayacceptedsocket.close()


def createRelayServer(relayhost, relayport):
    global running

    relaysocket = createNewListenSocket(relayhost, relayport)

    while running:
        relayacceptedsocket, echoaddr = relaysocket.accept()

        relay_thread = threading.Thread(target=handleEchoServer, args=(relayacceptedsocket, '213.82.87.21', 443))
        relay_thread.start()


createRelayServer('localhost', 1666)
