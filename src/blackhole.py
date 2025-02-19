import ipaddress
from typing import Final, Optional, override

from dnslib import (
    QTYPE,
    RR,
    DNSHeader,
    DNSRecord,
    DNSQuestion,
    NS,
    SOA,
)
from dnslib.server import BaseResolver, DNSServer as DnslibDNSServer
from loguru import logger

# Constants
SERVER_IP: Final[str] = "54.205.13.200"
SERVER_NAME: Final[str] = "blackhole.romulan.zone"
BASE_DOMAIN: Final[str] = "romulan.zone"
DNS_TTL: Final[int] = 60

# DNS Records
SOA_RECORD: Final[SOA] = SOA(
    mname="blackhole.romulan.zone.",
    rname="hostmaster.romulan.zone.",
    times=(
        202502191,  # Serial (YYYYMMDDnum)
        7200,       # Refresh
        900,        # Retry
        1209600,    # Expire
        86400       # Minimum
    )
)

NS_RECORDS: Final[list[NS]] = [
    NS("blackhole.romulan.zone.")
]


class BlackholeResolver(BaseResolver):
    """
    DNS resolver that returns NXDOMAIN for all queries except NS and SOA.
    """
    
    @override
    def resolve(self, request: DNSRecord, handler) -> DNSRecord:
        """Handle DNS queries by returning NXDOMAIN for everything except NS and SOA."""
        try:
            qname = request.q.qname
            qtype = request.q.qtype
            qt = QTYPE[qtype]
            
            logger.info(f"Received query for {qname} with type {qt}")
            
            # Prepare the DNS response
            reply = DNSRecord(
                DNSHeader(
                    id=request.header.id,
                    qr=1,     # QR: 1 (response)
                    aa=1,     # AA: 1 (authoritative)
                    ra=0,     # RA: 0 (recursion not available)
                ),
                q=request.q,
            )
            
            # Always add SOA to authority section for NXDOMAIN responses
            if qt != 'SOA':
                self._add_soa_to_authority(reply)
            
            domain_str = str(qname).rstrip('.')
            
            # Handle SOA queries
            if qt == 'SOA' and self._is_valid_domain(domain_str):
                self._handle_soa_query(reply, qname)
                logger.info(f"Responded to SOA query for {qname}")
            
            # Handle NS queries
            elif qt == 'NS' and self._is_valid_domain(domain_str):
                self._handle_ns_query(reply, qname)
                logger.info(f"Responded to NS query for {qname}")
            
            # All other queries get NXDOMAIN
            else:
                reply.header.rcode = 3  # NXDOMAIN
                logger.info(f"Returning NXDOMAIN for {qt} query: {qname}")
            
            return reply
            
        except Exception as e:
            logger.error(f"Error resolving DNS request: {e}")
            # Return SERVFAIL on error
            error_reply = DNSRecord(
                DNSHeader(
                    id=request.header.id,
                    qr=1,
                    aa=1,
                    ra=0,
                    rcode=2,  # SERVFAIL
                ),
                q=request.q,
            )
            return error_reply
    
    def _is_valid_domain(self, qname: str) -> bool:
        """Check if domain is within our authoritative zone."""
        return qname == BASE_DOMAIN or qname.endswith(f".{BASE_DOMAIN}")
    
    def _handle_soa_query(self, reply: DNSRecord, qname) -> None:
        """Add SOA record to the answer section."""
        reply.add_answer(
            RR(
                rname=qname,
                rtype=QTYPE.SOA,
                rclass=1,
                ttl=DNS_TTL,
                rdata=SOA_RECORD
            )
        )
    
    def _handle_ns_query(self, reply: DNSRecord, qname) -> None:
        """Add NS records to the answer section."""
        for ns_record in NS_RECORDS:
            reply.add_answer(
                RR(
                    rname=qname,
                    rtype=QTYPE.NS,
                    rclass=1,
                    ttl=DNS_TTL,
                    rdata=ns_record
                )
            )
    
    def _add_soa_to_authority(self, reply: DNSRecord) -> None:
        """Add SOA record to the authority section."""
        reply.add_auth(
            RR(
                rname=BASE_DOMAIN,
                rtype=QTYPE.SOA,
                rclass=1,
                ttl=DNS_TTL,
                rdata=SOA_RECORD
            )
        )


class BlackholeDNSServer:
    """
    DNS server that returns NXDOMAIN for all queries except NS and SOA.
    """
    
    def __init__(
        self,
        address: str = "0.0.0.0",
        port: int = 53,
        tcp: bool = True,
        udp: bool = True
    ) -> None:
        """
        Initialize the DNS server.
        
        Args:
            address: IP address to bind to
            port: Port to listen on
            tcp: Whether to enable TCP
            udp: Whether to enable UDP
        """
        self.address = address
        self.port = port
        self.tcp = tcp
        self.udp = udp
        self.resolver = BlackholeResolver()
        self.servers: list[DnslibDNSServer] = []
        
    def start(self) -> None:
        """Start the DNS server."""
        logger.info(f"Starting Blackhole DNS server on {self.address}:{self.port}")
        
        if self.udp:
            udp_server = DnslibDNSServer(
                resolver=self.resolver,
                address=self.address,
                port=self.port,
                tcp=False
            )
            self.servers.append(udp_server)
            udp_server.start_thread()
            logger.info(f"UDP server started on {self.address}:{self.port}")
            
        if self.tcp:
            tcp_server = DnslibDNSServer(
                resolver=self.resolver,
                address=self.address,
                port=self.port,
                tcp=True
            )
            self.servers.append(tcp_server)
            tcp_server.start_thread()
            logger.info(f"TCP server started on {self.address}:{self.port}")
    
    def stop(self) -> None:
        """Stop the DNS server."""
        logger.info("Stopping Blackhole DNS server")
        for server in self.servers:
            server.stop()
        self.servers = []
        logger.info("Blackhole DNS server stopped")


def main() -> None:
    """Main entry point for the DNS server."""
    # Configure logging
    logger.add("blackhole_dns.log", rotation="10 MB")
    
    try:
        # Start the DNS server
        server = BlackholeDNSServer(
            address="0.0.0.0",
            port=53,
            tcp=True,
            udp=True
        )
        server.start()
        
        # Keep running until interrupted
        logger.info("Server running. Press Ctrl+C to stop.")
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
        if 'server' in locals():
            server.stop()
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
    finally:
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()