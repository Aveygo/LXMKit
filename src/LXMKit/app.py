import RNS, LXMF, time, os, lmdb

class AnnounceHandler:
    """
    Used to receive display names from users. Handles RNS announce packets filtered by a specific aspect.
    """
    def __init__(self, aspect_filter: str, received_announce_callback):
        self.aspect_filter = aspect_filter
        self.received_announce_callback = received_announce_callback

    def received_announce(self, destination_hash, announced_identity, app_data, announce_packet_hash):
        """
        Processes received announce packets and invokes the callback.
        """
        try:
            self.received_announce_callback(self.aspect_filter, destination_hash, announced_identity, app_data, announce_packet_hash)
        except:
            pass

class Author:
    """
    Represents an author of an LXMF message with associated identity and routing.

    This class encapsulates an identity for sending messages via an LXMF router,
    with optional display name resolution via a callback.

    :param identity_hash: Hash of the author's identity.
    :type identity_hash: bytes
    :param router: LXMF router for message handling.
    :type router: LXMF.LXMRouter
    :param source: Source destination for message delivery.
    :type source: RNS.Destination
    :param display_name_callback: Optional callback to resolve display name, defaults to None.
    :type display_name_callback: callable, optional
    """
    def __init__(self, identity_hash:bytes, router:LXMF.LXMRouter, source:RNS.Destination, display_name_callback=None):
        self.identity_hash = identity_hash
        self.display_name_callback = display_name_callback
        self.router = router
        self._identity = RNS.Identity.recall(identity_hash)
        self._destination = RNS.Destination(
            self._identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery"
        )
        self.source = source
    
    @property
    def display_name(self) -> str | None:
        """
        Retrieves the author's display name using the callback.

        Filters the name to include only printable ASCII characters.

        :return: The display name or None if not available.
        :rtype: str | None
        """
        if self.display_name_callback is None:
            return None
        
        name = self.display_name_callback(self.identity_hash)
        if name is None:
            return None
        
        return ''.join(c for c in name.decode('ascii', errors='ignore') if c.isprintable())
    
    @property
    def hash(self):
        """
        Returns a human-readable representation of the identity hash.

        :return: Pretty-printed hex representation of the identity hash.
        :rtype: str
        """
        return str(RNS.prettyhexrep(self.identity_hash))
    
    def send(self, content, method=LXMF.LXMessage.OPPORTUNISTIC, include_ticket=True):
        """
        Sends an LXMF message with the specified content.

        :param content: The message content to send.
        :type content: str
        :param method: Delivery method (e.g., OPPORTUNISTIC), defaults to LXMF.LXMessage.OPPORTUNISTIC.
        :type method: int
        :param include_ticket: Whether to include a ticket, defaults to True.
        :type include_ticket: bool
        """
        lxm = LXMF.LXMessage(
            self._destination,
            self.source,
            content,
            desired_method=method,
            include_ticket=include_ticket
        )
        self.router.handle_outbound(lxm)

class Message:
    """
    Represents an LXMF message with content and author information.

    Provides functionality to access message content and reply to the message.

    :param lxmessage: The LXMF message object.
    :type lxmessage: LXMF.LXMessage
    :param router: LXMF router for message handling.
    :type router: LXMF.LXMRouter
    :param source: Source destination for message delivery.
    :type source: RNS.Destination
    :param display_name_callback: Optional callback to resolve author's display name, defaults to None.
    :type display_name_callback: callable, optional
    """
    def __init__(self, lxmessage:LXMF.LXMessage, router: LXMF.LXMRouter, source: RNS.Destination, display_name_callback=None):
        assert isinstance(lxmessage.source_hash, bytes), "invalid message hash"

        self.lxmessage = lxmessage
        self.content:str = lxmessage.content_as_string() # type: ignore
        self.author = Author(lxmessage.source_hash, router, source, display_name_callback)
    
    def reply(self, content, method=LXMF.LXMessage.OPPORTUNISTIC, include_ticket=True):
        """
        Sends a reply to the message.

        :param content: The reply content.
        :type content: str
        :param method: Delivery method, defaults to LXMF.LXMessage.OPPORTUNISTIC.
        :type method: int
        :param include_ticket: Whether to include a ticket, defaults to True.
        :type include_ticket: bool
        """
        self.author.send(content, method, include_ticket)

class LXMFApp:
    """
    Main application class for handling LXMF messaging over RNS.

    Initializes the Reticulum network, LXMF router, and storage for identities
    and names. Provides decorators for handling requests and message delivery.

    :param app_name: Name of the application
    :type app_name: str
    :param storage_path: Path for storing identity and name data, defaults to "./lxmf".
    :type storage_path: str
    :param announce: Number of seconds to wait between announces
    :type announce: int
    """
    def __init__(self, app_name:str, storage_path:str="./lxmf", announce:int=600):
        self.app_name = app_name
        self.storage_path = storage_path
        self.function_paths = {}
        self.rns = RNS.Reticulum(storage_path)
        self.names = lmdb.open(os.path.join(storage_path, "names"), map_size=10485760)
        identity_path = os.path.join(storage_path, "identity")

        assert announce > 30, "Should not perform an announce fewer than every 30 seconds."
        self.announce = announce
        
        if not os.path.exists(identity_path):
            self.identity = RNS.Identity()
            self.identity.to_file(identity_path)
        else:
            self.identity = RNS.Identity().from_file(identity_path)
        
        self.server_destination = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            "nomadnetwork",
            "node"
        )
        
        self.router = LXMF.LXMRouter(self.identity, storagepath=storage_path)
        
        self.source = self.router.register_delivery_identity(
            self.identity,
            display_name=self.app_name
        )

        assert not self.source is None, "Failed to register identity"

        RNS.Transport.register_announce_handler(AnnounceHandler("lxmf.delivery", self._on_lxmf_announce_received))

    def _on_lxmf_announce_received(self, aspect, destination_hash, announced_identity:RNS.Identity, app_data, announce_packet_hash):
        """
        Handles received LXMF display name announce packets and stores app data.
        """
        with self.names.begin(write=True) as txn:
            txn.put(destination_hash, app_data)

    def get_name(self, identity_hash:bytes):
        """
        Retrieves the name associated with an identity hash.
        """
        with self.names.begin() as txn:
            return txn.get(identity_hash)

    def _response_wrapper(self, path, data, request_id, link_id, remote_identity, requested_at):
        """
        Wraps request handling to match RNS link with the registered function.
        """
        found_link = None
        for link in self.server_destination.links:
            link:RNS.Link
            if link.link_id == link_id:
                found_link = link
                break
        
        assert not found_link is None, "RNS is bugging out? I don't know how you got here"

        return self.function_paths[path](path, found_link)

    def request_handler(self, path):
        """
        Decorator to register a request handler for a specific path.

        :param path: The request path to handle.
        :type path: str
        :return: Decorator function.
        :rtype: callable
        :raises AssertionError: If path contains wildcards or variables.
        """
        assert not "*" in path, f"Wild flags in path '{path}' not supported by RNS."
        assert not ("{" in path or "}" in path), f"Variables in path '{path}' not supported by RNS."
        
        def decorator(func):
            self.function_paths[path] = func
            self.server_destination.register_request_handler(
                path,
                response_generator=self._response_wrapper,
                allow=RNS.Destination.ALLOW_ALL
            )
            return func

        return decorator
    
    def delivery_callback(self, func):
        """
        Decorator to register a callback for LXMF message delivery.

        :param func: The callback function to handle delivered messages.
        :type func: callable
        :return: Decorated function.
        :rtype: callable
        """
        def wrapper(lxmessage: LXMF.LXMessage): 
            assert not self.source is None, "Failed to register identity"

            message = Message(lxmessage, self.router, self.source, self.get_name)
            return func(message)
        self.router.register_delivery_callback(wrapper)
        return func
        
    def run(self):
        """
        Runs the application, announcing destinations periodically.

        Logs destination hashes and announces the server and source destinations
        every 5 minutes.
        """
        assert not self.source is None, "Failed to register identity"

        RNS.log("Server destination hash: " + RNS.prettyhexrep(self.server_destination.hash))
        RNS.log("Delivery destination hash: " + RNS.prettyhexrep(self.source.hash))

        while True:
            self.server_destination.announce(app_data=self.app_name.encode("utf-8"))
            self.router.announce(self.source.hash)
            time.sleep(self.announce)

if __name__ == "__main__":
    LXMFApp("test").run()