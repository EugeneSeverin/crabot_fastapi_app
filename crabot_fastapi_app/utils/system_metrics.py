import os
import time
import threading
import docker
from prometheus_client import Gauge

# Метрики
cpu_usage_percent = Gauge("app_cpu_usage_percent", "CPU usage percent")
memory_usage_bytes = Gauge("app_memory_usage_bytes", "Memory usage in bytes")
disk_read_bytes = Gauge("app_disk_read_bytes", "Disk read bytes")
disk_write_bytes = Gauge("app_disk_write_bytes", "Disk write bytes")
network_sent = Gauge("app_network_sent_bytes", "Network bytes sent")
network_recv = Gauge("app_network_received_bytes", "Network bytes received")

container_name = os.getenv("NEZKA_CONTAINER_NAME")
DOCKER_SOCKET = "/var/run/docker.sock"

def get_docker_client():
    if os.path.exists(DOCKER_SOCKET):
        try:
            return docker.DockerClient(base_url=f'unix://{DOCKER_SOCKET}')
        except docker.errors.DockerException as e:
            print(f"[!] Docker client error: {e}")
    else:
        print(f"[!] Docker socket not found at {DOCKER_SOCKET}")
    return None

client = get_docker_client()

def get_docker_stats():
    if not client:
        return None
    try:
        container = client.containers.get(container_name)
        return container.stats(stream=False)
    except docker.errors.NotFound:
        print(f"[!] Container '{container_name}' not found.")
    except Exception as e:
        print(f"[!] Failed to get stats: {e}")
    return None

def collect_system_metrics():
    def run():
        while True:
            stats = get_docker_stats()
            if stats:
                try:
                    # CPU
                    cpu_total = stats["cpu_stats"]["cpu_usage"]["total_usage"]
                    system_cpu = stats["cpu_stats"].get("system_cpu_usage", 1) or 1
                    cpu_percent = (cpu_total / system_cpu) * 100
                    cpu_usage_percent.set(cpu_percent)

                    # Memory
                    memory = stats["memory_stats"].get("usage", 0)
                    memory_usage_bytes.set(memory)

                    # Disk I/O
                    blkio_stats = stats.get("blkio_stats", {}).get("io_service_bytes_recursive", [])
                    read_bytes = sum(x["value"] for x in blkio_stats if x.get("op", "").lower() == "read")
                    write_bytes = sum(x["value"] for x in blkio_stats if x.get("op", "").lower() == "write")
                    disk_read_bytes.set(read_bytes)
                    disk_write_bytes.set(write_bytes)

                    # Network
                    networks = stats.get("networks", {})
                    sent = sum(iface["tx_bytes"] for iface in networks.values())
                    recv = sum(iface["rx_bytes"] for iface in networks.values())
                    network_sent.set(sent)
                    network_recv.set(recv)

                except Exception as parse_err:
                    print(f"[!] Error parsing stats: {parse_err}")
            time.sleep(5)

    threading.Th
