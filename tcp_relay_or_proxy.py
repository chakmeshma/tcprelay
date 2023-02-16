import os
import socket
import sys
import threading

NET_MSG_SIZE = 1024
running = False
logging_enabled = True


def _graceful_socket_close(s: socket.socket):
    if s:
        try:
            s.shutdown(socket.SHUT_RDWR)
        except:
            pass
        finally:
            s.close()


def _createNewListenSocket(hostname: str, port: int) -> socket.socket:
    s = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((hostname, port))
    s.listen()

    return s


def _createNewConnectSocket(hostname: str, port: int) -> socket.socket:
    s = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))

    return s


def _handleRelay(relayacceptedsocket: socket.socket, proxy_mode: bool = True, target_name: str = None,
                 target_port: int = None):
    global running
    global NET_MSG_SIZE

    tunnelsocket = None

    try:
        if proxy_mode:
            inbound_meta_data: bytes = relayacceptedsocket.recv(4096)
            inbound_meta_data_str: str = inbound_meta_data.decode('ascii')
            fspace_pos = inbound_meta_data_str.index(' ')
            sspace_pos = inbound_meta_data_str.index(' ', fspace_pos + 1)
            remote_taddress_str = inbound_meta_data_str[fspace_pos + 1:sspace_pos]
            remote_taddress_ss = remote_taddress_str.split(':')
            remote_taddress = (remote_taddress_ss[0], int(remote_taddress_ss[1]))
            fnl_pos = inbound_meta_data_str.index('\r')
            lrs_pos = inbound_meta_data_str[:fnl_pos].rindex(' ')
            meta_protocol_str = inbound_meta_data_str[lrs_pos + 1:fnl_pos]

            tunnelsocket = _createNewConnectSocket(remote_taddress[0], remote_taddress[1])

            if logging_enabled:
                print(f'New connection made to {tunnelsocket.getpeername()}')

            outbound_meta_str: str = f'{meta_protocol_str} 200 OK\r\n\r\n'
            outbound_meta_data: bytes = outbound_meta_str.encode('ascii')

            relayacceptedsocket.sendall(outbound_meta_data)
        else:
            tunnelsocket = _createNewConnectSocket(target_name, target_port)
            if logging_enabled:
                print(f'New connection made to {tunnelsocket.getpeername()}')

        relayacceptedsocket.setblocking(False)
        tunnelsocket.setblocking(False)

        relayacceptedsocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        tunnelsocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

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
        _graceful_socket_close(tunnelsocket)
        _graceful_socket_close(relayacceptedsocket)

        if logging_enabled:
            print('Closed connection')


def create(bind_address: str, bind_port: int, proxy_mode: bool = True, target_name: str = None,
           target_port: int = None):
    if not proxy_mode:
        if (not target_name) or (not target_port):
            raise Exception('Address and Port must be provided when relay mode (not proxy)')

    global running

    running = True

    localRelayListenSocket = _createNewListenSocket(bind_address, bind_port)

    try:
        while running:
            relayacceptedsocket, relayacceptedaddr = localRelayListenSocket.accept()

            if logging_enabled:
                print(f'Accepted new connection from {relayacceptedaddr}')

            relay_thread = threading.Thread(target=_handleRelay,
                                            args=(relayacceptedsocket, proxy_mode, target_name,
                                                  target_port))
            relay_thread.start()
    except:
        pass
    finally:
        _graceful_socket_close(localRelayListenSocket)

    running = False


def _print_usage():
    fname = os.path.basename(__file__)
    print(
        f'Usage:\n{fname} -p <local address>:<local port>\n{fname} -r <local address>:<local port> <remote '
        f'address>:<remote port>')


def _check_args():
    if len(sys.argv) < 3:
        return False
    if sys.argv[1] != '-p' and sys.argv[1] != '-r':
        return False

    if sys.argv[1] == '-p':
        if sys.argv[2].find(':') <= 0 or sys.argv[2].find(':') == (len(sys.argv[2]) - 1):
            return False
        if not sys.argv[2].split(':')[1].isdecimal():
            return False

        lp = int(sys.argv[2].split(':')[1])
        if lp < 0 or lp > 65535:
            return False

    if sys.argv[1] == '-r':
        if len(sys.argv) < 4:
            return False
        if sys.argv[2].find(':') <= 0 or sys.argv[2].find(':') == (len(sys.argv[2]) - 1):
            return False
        if sys.argv[3].find(':') <= 0 or sys.argv[3].find(':') == (len(sys.argv[3]) - 1):
            return False

        if not sys.argv[2].split(':')[1].isdecimal():
            return False
        if not sys.argv[3].split(':')[1].isdecimal():
            return False

        lp = int(sys.argv[2].split(':')[1])
        if lp < 0 or lp > 65535:
            return False

        rp = int(sys.argv[3].split(':')[1])
        if rp < 0 or rp > 65535:
            return False

    return True


# Program starts here
if not _check_args():
    _print_usage()
    sys.exit(1)

mode = sys.argv[1]

laddrlist = sys.argv[2].split(':')
laddr = (laddrlist[0], int(laddrlist[1]))

if mode == '-p':
    create(laddr[0], laddr[1], True)
elif mode == '-r':
    raddrlist = sys.argv[3].split(':')
    raddr = (raddrlist[0], int(raddrlist[1]))
    create(laddr[0], laddr[1], False, raddr[0], raddr[1])
else:
    sys.exit(1)
