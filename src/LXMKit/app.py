import RNS
import LXMF
import time
import os
import lmdb

class AnnounceHandler:
    def __init__(self, aspect_filter: str, received_announce_callback):
        self.aspect_filter = aspect_filter
        self.received_announce_callback = received_announce_callback

    def received_announce(self, destination_hash, announced_identity, app_data, announce_packet_hash):
        try:
            self.received_announce_callback(self.aspect_filter, destination_hash, announced_identity, app_data, announce_packet_hash)
        except:
            pass

class Author:
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
        # A callback is used as user may update their name after it is saved in the db
        if self.display_name_callback is None:
            return None
        
        name = self.display_name_callback(self.identity_hash)
        if name is None:
            return None
        
        return ''.join(c for c in name.decode('ascii', errors='ignore') if c.isprintable())
        

    @property
    def hash(self):
        return str(RNS.prettyhexrep(self.identity_hash))
    
    def send(self, content, method=LXMF.LXMessage.OPPORTUNISTIC, include_ticket=True):
        lxm = LXMF.LXMessage(
            self._destination,
            self.source,
            content,
            desired_method=method,
            include_ticket=include_ticket
        )
        self.router.handle_outbound(lxm)

class Message:
    def __init__(self, lxmessage:LXMF.LXMessage, router: LXMF.LXMRouter, source: RNS.Destination, display_name_callback=None):
        assert isinstance(lxmessage.source_hash, bytes), "invalid message hash"

        self.lxmessage = lxmessage
        self.content:str = lxmessage.content_as_string() # type: ignore

        self.author = Author(lxmessage.source_hash, router, source, display_name_callback)
    
    def reply(self, content, method=LXMF.LXMessage.OPPORTUNISTIC, include_ticket=True):
        self.author.send(content, method, include_ticket)

class LXMFApp:
    def __init__(self, storage_path="./tmp", app_name="MyBot"):
        self.app_name = app_name
        self.storage_path = storage_path
        self.function_paths = {}
        self.rns = RNS.Reticulum(storage_path)
        self.names = lmdb.open(os.path.join(storage_path, "names"), map_size=10485760)
        identity_path = os.path.join(storage_path, "identity")
        
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

        RNS.Transport.register_announce_handler(AnnounceHandler("lxmf.delivery", self.on_lxmf_announce_received))

    def on_lxmf_announce_received(self, aspect, destination_hash, announced_identity:RNS.Identity, app_data, announce_packet_hash):
        with self.names.begin(write=True) as txn:
            txn.put(destination_hash, app_data)

    def get_name(self, identity_hash:bytes):
        with self.names.begin() as txn:
            return txn.get(identity_hash)

    def _response_wrapper(self, path, data, request_id, link_id, remote_identity, requested_at):

        found_link = None
        for link in self.server_destination.links:
            link:RNS.Link
            if link.link_id == link_id:
                found_link = link
                break
        
        assert not found_link is None, "RNS is bugging out? I don't know how you got here"

        return self.function_paths[path](path, found_link)

    def request_handler(self, path):
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
        def wrapper(lxmessage: LXMF.LXMessage): 
            assert not self.source is None, "Failed to register identity"

            message = Message(lxmessage, self.router, self.source, self.get_name)
            return func(message)
        self.router.register_delivery_callback(wrapper)
        return func
        
    def run(self):
        assert not self.source is None, "Failed to register identity"

        RNS.log("Server destination hash: " + RNS.prettyhexrep(self.server_destination.hash))
        RNS.log("Delivery destination hash: " + RNS.prettyhexrep(self.source.hash))

        while True:
            self.server_destination.announce(app_data=self.app_name.encode("utf-8"))
            self.router.announce(self.source.hash)
            time.sleep(60 * 5)

if __name__ == "__main__":
    LXMFApp().run()
    