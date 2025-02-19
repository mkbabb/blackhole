# `blackhole`

A simple DNS server that returns NXDOMAIN for all queries except NS and SOA, designed
for `blackhole.romulan.zone`.

## Quickstart 🚀

This project requires Python `^3.12` to run.

Several dependencies are needed, specifically `dnslib` for DNS server functionality and
`loguru` for logging.

### via [`poetry`](https://python-poetry.org/docs/)

Install poetry, then run

> poetry install

And you're done.

## Configuration 🔧

The DNS server uses several constants that can be easily modified:

-   `SERVER_IP`: The IP address of the blackhole server
-   `SERVER_NAME`: The hostname of the blackhole server
-   `BASE_DOMAIN`: The base domain name for which this server is authoritative
-   `DNS_TTL`: Time-to-live value for DNS records

## Running the Server 🖥️

To run the server:

```python
from blackhole import BlackholeDNSServer

# Start the DNS server
server = BlackholeDNSServer(
    address="0.0.0.0",  # Listen on all interfaces
    port=53,            # Standard DNS port
    tcp=True,           # Enable TCP
    udp=True            # Enable UDP
)
server.start()
```

Since the server uses port 53, you may need to run it with elevated privileges:

```bash
sudo poetry run python -m src.blackhole
```

## DNS Record Types 📝

### SOA Record

The server responds to SOA queries with a properly formatted SOA record containing:

-   MNAME: Primary nameserver (blackhole.romulan.zone)
-   RNAME: Responsible person's email (hostmaster.romulan.zone)
-   Serial: Current date in YYYYMMDD format plus revision number
-   Refresh, retry, expire, and minimum TTL values

### NS Records

The server responds to NS queries with NS records pointing to blackhole.romulan.zone.

### All Other Queries

All other query types (A, AAAA, MX, TXT, etc.) receive NXDOMAIN responses.
