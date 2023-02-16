import socket
import threading

NET_MSG_SIZE = 1024

running = 1

relay_local_bind_address = '0.0.0.0'
relay_local_bind_port = 5633


def createNewListenSocket(hostname, port):
    s = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((hostname, port))
    s.listen()

    return s


def createNewConnectSocket(hostname, port):
    s = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))

    return s


def handleRelay(relayacceptedsocket):
    tunnelsocket = None

    try:
        global running

        inbound_meta_data: bytes = relayacceptedsocket.recv(1024)
        inbound_meta_data_str: str = inbound_meta_data.decode('ascii')
        fspace_pos = inbound_meta_data_str.index(' ')
        sspace_pos = inbound_meta_data_str.index(' ', fspace_pos + 1)
        remote_taddress_str = inbound_meta_data_str[fspace_pos + 1:sspace_pos]
        remote_taddress_ss = remote_taddress_str.split(':')
        remote_taddress = (remote_taddress_ss[0], int(remote_taddress_ss[1]))
        fnl_pos = inbound_meta_data_str.index('\r')
        lrs_pos = inbound_meta_data_str[:fnl_pos].rindex(' ')
        meta_protocol_str = inbound_meta_data_str[lrs_pos + 1:fnl_pos]

        tunnelsocket = createNewConnectSocket(remote_taddress[0], remote_taddress[1])

        print(f'New connection made to {tunnelsocket.getpeername()}')

        outbound_meta_str: str = f"{meta_protocol_str} 200 OK\r\n\r\n"
        outbound_meta_data: bytes = outbound_meta_str.encode('ascii')

        relayacceptedsocket.sendall(outbound_meta_data)

        relayacceptedsocket.setblocking(False)
        tunnelsocket.setblocking(False)

        while running:
            try:
                relay_data = relayacceptedsocket.recv(NET_MSG_SIZE)
                if relay_data:
                    tunnelsocket.sendall(relay_data)
            except socket.error as e:
                if e.errno != socket.EWOULDBLOCK and e.errno != socket.EAGAIN:
                    raise e

            try:
                tunnel_data = tunnelsocket.recv(NET_MSG_SIZE)
                if tunnel_data:
                    relayacceptedsocket.sendall(tunnel_data)
            except socket.error as e:
                if e.errno != socket.EWOULDBLOCK and e.errno != socket.EAGAIN:
                    raise e
    except:
        pass
    finally:
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

            print(f"Accepted new connection from {relayacceptedaddr}")

            relay_thread = threading.Thread(target=handleRelay,
                                            args=(relayacceptedsocket,))
            relay_thread.start()
    except:
        pass
    finally:
        if relaysocket:
            relaysocket.close()


createRelayServer(relay_local_bind_address, relay_local_bind_port)
