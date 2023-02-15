import socket
import threading

NET_MSG_SIZE = 1024

running = 1


def createNewListenSocket(hostname, port):
    s = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((hostname, port))
    s.listen(0)

    return s


def createNewConnectSocket(hostname, port):
    s = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))

    return s


def handleEchoServer(relayacceptedsocket, tunnelhost, tunnelport):
    tunnelsocket = None

    try:
        global running

        tunnelsocket = createNewConnectSocket(tunnelhost, tunnelport)

        tunnelsocket.setblocking(False)
        relayacceptedsocket.setblocking(False)

        while running:
            try:
                relay_data = relayacceptedsocket.recv(NET_MSG_SIZE)
                # if relay_data:
                tunnelsocket.send(relay_data)
            except socket.error as e:
                if e.args[0] != socket.EAGAIN and e.args[0] != socket.EWOULDBLOCK:
                    raise e

            try:
                tunnel_data = tunnelsocket.recv(NET_MSG_SIZE)
                # if tunnel_data:
                relayacceptedsocket.send(tunnel_data)
            except socket.error as e:
                if e.args[0] != socket.EAGAIN and e.args[0] != socket.EWOULDBLOCK:
                    raise e

        if tunnelsocket:
            tunnelsocket.close()
        if relayacceptedsocket:
            relayacceptedsocket.close()
        print('Closed a connection')
    except:
        if tunnelsocket:
            tunnelsocket.close()
        if relayacceptedsocket:
            relayacceptedsocket.close()
        print('Closed a connection')


def createRelayServer(relayhost, relayport):
    global running

    relaysocket = createNewListenSocket(relayhost, relayport)

    try:
        while running:
            relayacceptedsocket, relayacceptedaddr = relaysocket.accept()

            print(f"Accepted new connection {relayacceptedaddr}")

            relay_thread = threading.Thread(target=handleEchoServer, args=(relayacceptedsocket, 'www.google.com', 443))
            relay_thread.start()

        if relaysocket:
            relaysocket.close()
    except:
        if relaysocket:
            relaysocket.close()


createRelayServer('0.0.0.0', 800)
