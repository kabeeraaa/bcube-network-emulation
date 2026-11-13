# BCube Network Emulation

A standalone portfolio demo based on a graduate data center networking lab. It uses Python, Mininet, and Open vSwitch to emulate a BCube-style topology with 16 hosts, 32 switches, and 64 links. Each link is configured for 8 Mbps bandwidth and 4 ms delay.

The demo installs default-drop OpenFlow rules and allows IPv4 traffic for five selected host pairs. It tests those paths with ping and iPerf and checks that a sixth pair with a physical link cannot exchange ping traffic.

## Run locally

Print the topology size and selected pairs with Python 3. This step does not require Mininet.

```sh
python3 bcube_demo.py --plan
```

Use a dedicated Linux lab VM with Python 3, Mininet, Open vSwitch, iPerf 2, ping, iproute2, and telnet. Ensure the Open vSwitch service is running. Then launch the emulation with:

```sh
sudo python3 bcube_demo.py --output results.csv
```

The output records ping replies, average round-trip time, and the iPerf rates reported by the server and client. The script stops its Mininet network after the checks.

## Saved coursework measurements

These are historical measurements from five paths in the original lab. The standalone demo uses its own host pairs and should produce its own measurements.

| Coursework path | iPerf throughput | Average ping RTT |
| --- | ---: | ---: |
| A | 7.00 Mbps | 43.232 ms |
| B | 7.17 Mbps | 134.498 ms |
| C | 6.33 Mbps | 38.066 ms |
| D | 6.22 Mbps | 38.131 ms |
| E | 6.92 Mbps | 67.380 ms |

The original coursework also explored FlowVisor slicing. This demo configures Open vSwitch directly.

## References

- [Mininet Python API](https://mininet.org/api/classmininet_1_1net_1_1Mininet.html)
- [Open vSwitch guide to OpenFlow](https://docs.openvswitch.org/en/latest/faq/openflow/)
