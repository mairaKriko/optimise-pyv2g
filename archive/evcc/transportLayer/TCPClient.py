#######################################################
# 
# TCPClient.py
# Python implementation of the Class TCPClient
# Generated by Enterprise Architect
# Created on:      07-Jan-2021 11:23:10
# Original author: Fabian.Stichtenoth
# 
#######################################################
import threading
import socket
import logging
import io

from shared.misc.V2GTPMessage import V2GTPMessage
from evcc.transportLayer.StatefulTransportLayerClient import StatefulTransportLayerClient

_unique_tcp_client_instance = None
thread_lock = threading.Lock()


class TCPClient(StatefulTransportLayerClient):

    def __init__(self):
        super().__init__()
        self._tcp_socket_to_server = None
        self._unique_tcp_client_instance = TCPClient()
        self._interrupt = False

    @classmethod
    def get_instance(cls):
        """Checks for an instance and creates one if there isn't one already. The
        synchronized block is only entered once as long as there is no existing
        instance of the TCPClient (safes valuable resource).
        :return _unique_tcp_client_instance:
        """
        global _unique_tcp_client_instance
        if _unique_tcp_client_instance is None:
            thread_lock.acquire()
            if _unique_tcp_client_instance is None:
                _unique_tcp_client_instance = TCPClient()
            thread_lock.release()
        return _unique_tcp_client_instance

    def get_socket_to_server(self):
        """
        Returns the socket that is connected to the server
        :return _tcp_socket_to_server:
        """
        return self._tcp_socket_to_server

    def get_tcp_socket_to_server(self):
        """
        Returns the socket that is connected to the server
        :return _tcp_socket_to_server:
        """
        return self._tcp_socket_to_server
        pass

    def initialize(self, host=None, port=None) -> bool:
        """Initializes the TCP client as soon as a SECCDiscoveryRes message arrived.
        :param host:
        :param port:
        :return: bool
        """
        super().initialize()

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            address = (host, port)
            s.connect(address)

            self.set_tcp_socket_to_server(s)
            # TODO: not sure if next two lines are correct
            self.set_in_stream(self.get_tcp_socket_to_server().listen(5))
            self.set_out_stream(self.get_tcp_socket_to_server())

            logging.info("TCP client connection established \n\t from link-local address " +
                         str(self.get_client_address()) + " and port " + str(self.get_client_port()) +
                         "\n\t to host " + str(host.gethostname()) + " and port " + str(port))

            return True

        except socket.herror as e:
            logging.error("TCP client connection failed (UnknownHostException)!", e)

        except IOError as e:
            logging.error("TCP client connection failed (IOException)!", e)

        return False

    def run(self) -> None:
        """
        Run-method of a thread. While the thread is not interrupted, a timeout is set if necessary. Also the incoming
        messages are processed. Thread is stopped at the end
        :return: None
        """
        while not self._interrupt:
            if self.get_timeout() > 0:
                try:
                    self.get_socket_to_server().settimeout(self.get_timeout())

                    if not self.process_incoming_message():
                        break

                except socket.timeout:
                    self.stop_and_notify("A timeout occurred while waiting for response message", None)
                    break

                except IOError as e2:
                    self.stop_and_notify("An IOException occurred while trying to read message", e2)
                    break

        self.stop()

    def send(self, message: V2GTPMessage, timeout: int) -> None:
        """
        Message is written to Output-Stream and it is tried to be sent. Possible exceptions are caught
        :param message: V2GTPMessage
        :param timeout: int
        :return: None
        """
        self.set_v2g_tp_message(None)

        try:
            self.get_out_stream().write(message.get_message())
            self.get_out_stream().flush()
            logging.debug("Message sent")
            self.set_timeout(timeout)

        except IOError as e:
            logging.error("An undefined IOException occurred while trying to send message", e)

    def set_socket_to_server(self, socket_to_server) -> None:
        """
        Sets the socket that is connected to the server
        :param socket_to_server:
        :return: None
        """
        self._tcp_socket_to_server = socket_to_server

    def set_tcp_socket_to_server(self, tcp_socket_to_server) -> None:
        """
        Sets the socket that is connected to the server
        :param tcp_socket_to_server:
        :return: None
        """
        self._tcp_socket_to_server = tcp_socket_to_server

    def stop(self) -> None:
        """
        Checks if stop was already initiated and if not, initiates it. Closes Input Stream, Output Stream and socket and
        sets interrupt-parameter to True. Exceptions are caught
        :return: None
        """
        if not self.is_stop_already_initiated():
            logging.debug("Stopping TCP client ...")
            self.set_stop_already_initiated(True)

            try:
                self.get_in_stream().close()
                self.get_out_stream().close()
                self.get_tcp_socket_to_server().close()
                self._interrupt = True

            except IOError as e:
                logging.error("Error occurred while trying to close TCP socket to server", e)

            logging.debug("TCP client stopped")