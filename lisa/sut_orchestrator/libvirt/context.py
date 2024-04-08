from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import libvirt  # type: ignore

from lisa.environment import Environment
from lisa.node import Node

from .console_logger import QemuConsoleLogger
from .schema import DiskImageFormat


@dataclass
class DataDiskContext:
    file_path: str = ""
    size_gib: int = 0


@dataclass
class EnvironmentContext:
    ssh_public_key: str = ""

    # Timeout for the OS to boot and acquire an IP address, in seconds.
    network_boot_timeout: float = 30.0

    # List of (port, IP) used in port forwading
    port_forwarding_list: List[Tuple[int, str]] = field(default_factory=list)


@dataclass
class InitSystem:
    CLOUD_INIT: str = "cloud-init"
    IGNITION: str = "ignition"


@dataclass
class NodeContext:
    vm_name: str = ""
    firmware_source_path: str = ""
    firmware_path: str = ""
    cloud_init_file_path: str = ""
    ignition_file_path: str = ""
    os_disk_source_file_path: Optional[str] = None
    os_disk_base_file_path: str = ""
    os_disk_base_file_fmt: DiskImageFormat = DiskImageFormat.QCOW2
    os_disk_file_path: str = ""
    os_disk_img_resize_gib: Optional[int] = None
    console_log_file_path: str = ""
    extra_cloud_init_user_data: List[Dict[str, Any]] = field(default_factory=list)
    use_bios_firmware: bool = False
    data_disks: List[DataDiskContext] = field(default_factory=list)
    next_disk_index: int = 0
    machine_type: Optional[str] = None
    enable_secure_boot: bool = False
    init_system: str = InitSystem.CLOUD_INIT

    console_logger: Optional[QemuConsoleLogger] = None
    domain: Optional[libvirt.virDomain] = None


def get_environment_context(environment: Environment) -> EnvironmentContext:
    return environment.get_context(EnvironmentContext)


def get_node_context(node: Node) -> NodeContext:
    return node.get_context(NodeContext)
