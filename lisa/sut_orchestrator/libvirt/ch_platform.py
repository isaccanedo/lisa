# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import os
import re
import xml.etree.ElementTree as ET  # noqa: N817
from pathlib import Path
from typing import List, Type

from lisa import schema
from lisa.environment import Environment
from lisa.feature import Feature
from lisa.node import Node
from lisa.sut_orchestrator.libvirt.context import NodeContext, get_node_context
from lisa.sut_orchestrator.libvirt.platform import BaseLibvirtPlatform
from lisa.tools import QemuImg
from lisa.util.logger import Logger, filter_ansi_escape

from .. import CLOUD_HYPERVISOR
from .console_logger import QemuConsoleLogger
from .schema import BaseLibvirtNodeSchema, CloudHypervisorNodeSchema, DiskImageFormat

CH_VERSION_PATTERN = re.compile(r"cloud-hypervisor (?P<ch_version>.+)")


class CloudHypervisorPlatform(BaseLibvirtPlatform):
    @classmethod
    def type_name(cls) -> str:
        return CLOUD_HYPERVISOR

    @classmethod
    def supported_features(cls) -> List[Type[Feature]]:
        return BaseLibvirtPlatform._supported_features

    @classmethod
    def node_runbook_type(cls) -> type:
        return CloudHypervisorNodeSchema

    def _libvirt_uri_schema(self) -> str:
        return "ch"

    def _configure_node(
        self,
        node: Node,
        node_idx: int,
        node_space: schema.NodeSpace,
        node_runbook: BaseLibvirtNodeSchema,
        vm_name_prefix: str,
    ) -> None:
        super()._configure_node(
            node,
            node_idx,
            node_space,
            node_runbook,
            vm_name_prefix,
        )

        assert isinstance(node_runbook, CloudHypervisorNodeSchema)
        node_context = get_node_context(node)
        if self.host_node.is_remote:
            node_context.firmware_source_path = node_runbook.firmware
            node_context.firmware_path = os.path.join(
                self.vm_disks_dir, os.path.basename(node_runbook.firmware)
            )
        else:
            node_context.firmware_path = node_runbook.firmware

    def _create_node(
        self,
        node: Node,
        node_context: NodeContext,
        environment: Environment,
        log: Logger,
    ) -> None:
        if node_context.firmware_source_path:
            self.host_node.shell.copy(
                Path(node_context.firmware_source_path),
                Path(node_context.firmware_path),
            )

        super()._create_node(
            node,
            node_context,
            environment,
            log,
        )

    def _create_node_domain_xml(
        self,
        environment: Environment,
        log: Logger,
        node: Node,
    ) -> str:
        node_context = get_node_context(node)

        domain = ET.Element("domain")
        domain.attrib["type"] = "ch"

        name = ET.SubElement(domain, "name")
        name.text = node_context.vm_name

        memory = ET.SubElement(domain, "memory")
        memory.attrib["unit"] = "MiB"
        assert isinstance(node.capability.memory_mb, int)
        memory.text = str(node.capability.memory_mb)

        vcpu = ET.SubElement(domain, "vcpu")
        assert isinstance(node.capability.core_count, int)
        vcpu_count = node.capability.core_count
        vcpu.text = str(vcpu_count)

        os = ET.SubElement(domain, "os")

        os_type = ET.SubElement(os, "type")
        os_type.text = "hvm"

        os_kernel = ET.SubElement(os, "kernel")
        os_kernel.text = node_context.firmware_path

        devices = ET.SubElement(domain, "devices")

        console = ET.SubElement(devices, "console")
        console.attrib["type"] = "pty"

        console_target = ET.SubElement(console, "target")
        console_target.attrib["type"] = "serial"
        console_target.attrib["port"] = "0"

        network_interface = ET.SubElement(devices, "interface")
        network_interface.attrib["type"] = "network"

        network_interface_source = ET.SubElement(network_interface, "source")
        network_interface_source.attrib["network"] = "default"

        network_model = ET.SubElement(network_interface, "model")
        network_model.attrib["type"] = "virtio"

        network_driver = ET.SubElement(network_interface, "driver")
        network_driver.attrib["queues"] = str(vcpu_count)
        network_driver.attrib["iommu"] = "on"

        self._add_virtio_disk_xml(
            node_context,
            devices,
            node_context.os_disk_file_path,
            vcpu_count,
        )

        self._add_virtio_disk_xml(
            node_context,
            devices,
            node_context.cloud_init_file_path,
            vcpu_count,
        )

        xml = ET.tostring(domain, "unicode")
        return xml

    def _get_domain_undefine_flags(self) -> int:
        return 0

    def _create_domain_and_attach_logger(
        self,
        node_context: NodeContext,
    ) -> None:
        assert node_context.domain
        node_context.domain.createWithFlags(0)

        node_context.console_logger = QemuConsoleLogger()
        node_context.console_logger.attach(
            node_context.domain, node_context.console_log_file_path
        )

    # Create the OS disk.
    def _create_node_os_disk(
        self, environment: Environment, log: Logger, node: Node
    ) -> None:
        node_context = get_node_context(node)

        if node_context.os_disk_base_file_fmt == DiskImageFormat.QCOW2:
            self.host_node.tools[QemuImg].convert(
                "qcow2",
                node_context.os_disk_base_file_path,
                "raw",
                node_context.os_disk_file_path,
            )
        else:
            self.host_node.execute(
                f"cp {node_context.os_disk_base_file_path}"
                f" {node_context.os_disk_file_path}",
                expected_exit_code=0,
                expected_exit_code_failure_message="Failed to copy os disk image",
            )

        if node_context.os_disk_img_resize_gib:
            self.host_node.tools[QemuImg].resize(
                src_file=node_context.os_disk_file_path,
                size_gib=node_context.os_disk_img_resize_gib,
            )

    def _get_vmm_version(self) -> str:
        result = "Unknown"
        if self.host_node:
            output = self.host_node.execute(
                "cloud-hypervisor --version",
                shell=True,
            ).stdout
            output = filter_ansi_escape(output)
            match = re.search(CH_VERSION_PATTERN, output.strip())
            if match:
                result = match.group("ch_version")
        return result
