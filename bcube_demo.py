"""Build and benchmark a BCube-style topology with Mininet."""

import argparse
import csv
import os
import re
import subprocess
from pathlib import Path


HOST_COUNT = 16
LEVELS = 4
LINK_BANDWIDTH_MBPS = 8
LINK_DELAY = "4ms"
ALLOWED_PAIRS = ((0, 8), (2, 3), (4, 6), (9, 13), (12, 14))
BLOCKED_PAIR = (0, 1)


def host_name(index):
    return f"bc-h{index:02}"


def switch_layout():
    for level in range(LEVELS):
        bit = 1 << level
        for host in range(HOST_COUNT):
            if not host & bit:
                yield f"bc-s{level}{host:02}", (host, host | bit)


def configure_flows(network):
    allowed = {frozenset(pair) for pair in ALLOWED_PAIRS}
    for switch, (left_index, right_index) in switch_layout():
        subprocess.run(["ovs-ofctl", "add-flow", switch, "priority=0,actions=drop"], check=True)
        if frozenset((left_index, right_index)) not in allowed:
            continue
        left = network.get(host_name(left_index))
        right = network.get(host_name(right_index))
        for source, target in ((left, right), (right, left)):
            rule = f"priority=100,ip,nw_src={source.IP()},nw_dst={target.IP()},actions=NORMAL"
            subprocess.run(["ovs-ofctl", "add-flow", switch, rule], check=True)


def configure_route(source, target, switch):
    interface, _ = source.connectionsTo(switch)[0]
    _, error, status = source.pexec(
        "ip", "route", "replace", f"{target.IP()}/32",
        "dev", interface.name, "src", source.IP(),
    )
    if status:
        raise RuntimeError(f"Could not configure the {source.name} route: {error.strip()}")


def benchmark(network):
    switches = {frozenset(pair): switch for switch, pair in switch_layout()}
    rows = []
    for pair in (*ALLOWED_PAIRS, BLOCKED_PAIR):
        left, right = (network.get(host_name(index)) for index in pair)
        switch = network.get(switches[frozenset(pair)])
        configure_route(left, right, switch)
        configure_route(right, left, switch)
        expected_reachable = pair in ALLOWED_PAIRS
        output, error, status = left.pexec("ping", "-c", "5", "-w", "12", right.IP())
        if status not in (0, 1):
            raise RuntimeError(f"Ping failed for {left.name} to {right.name}: {error.strip()}")
        latency = re.search(r"min/avg/max/\w+\s*=\s*[\d.]+/([\d.]+)/", output)
        received = re.search(r"(\d+) (?:packets )?received", output)
        if not received or (int(received[1]) > 0) != expected_reachable:
            raise RuntimeError(f"Unexpected reachability for {left.name} to {right.name}.")
        if expected_reachable and not latency:
            raise RuntimeError(f"Ping did not report RTT for {left.name} to {right.name}.")
        throughput = network.iperf(hosts=(left, right), seconds=5, fmt="m") if expected_reachable else []
        rows.append((
            left.name, right.name, int(received[1]),
            latency[1] if latency else "",
            throughput[0] if throughput else "",
            throughput[1] if len(throughput) > 1 else "",
        ))
    return rows


def run_demo(output):
    from mininet.link import TCLink
    from mininet.log import setLogLevel
    from mininet.net import Mininet
    from mininet.node import OVSSwitch
    from mininet.topo import Topo

    if os.geteuid() != 0:
        raise SystemExit("Run the emulation as root inside a dedicated Linux lab VM.")

    topology = Topo()
    for index in range(HOST_COUNT):
        topology.addHost(host_name(index), ip=f"10.0.0.{index + 1}/24")
    for switch, pair in switch_layout():
        topology.addSwitch(switch, protocols="OpenFlow10", failMode="secure")
        for index in pair:
            topology.addLink(host_name(index), switch, bw=LINK_BANDWIDTH_MBPS, delay=LINK_DELAY)

    setLogLevel("info")
    network = Mininet(
        topo=topology, controller=None, switch=OVSSwitch, link=TCLink,
        autoSetMacs=True, autoStaticArp=True,
    )
    try:
        network.start()
        configure_flows(network)
        rows = benchmark(network)
    finally:
        network.stop()

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("source", "destination", "ping_replies", "avg_rtt_ms", "server_rate", "client_rate"))
        writer.writerows(rows)
    print(f"Results written to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="Print the topology and test pairs without running Mininet.")
    parser.add_argument("--output", type=Path, default=Path("results.csv"), help="Write measurements to this CSV.")
    args = parser.parse_args()
    if args.plan:
        switches = list(switch_layout())
        print(f"{HOST_COUNT} hosts, {len(switches)} switches, {sum(len(pair) for _, pair in switches)} links")
        for left, right in ALLOWED_PAIRS:
            print(f"Allow: {host_name(left)} <-> {host_name(right)}")
        print(f"Block: {host_name(BLOCKED_PAIR[0])} <-> {host_name(BLOCKED_PAIR[1])}")
        return
    if os.name != "posix":
        parser.error("Run the emulation in Linux or use --plan on this machine.")
    run_demo(args.output)


if __name__ == "__main__":
    main()
