# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import re
from typing import Optional, Type

from lisa.base_tools import Cat
from lisa.executable import Tool
from lisa.operating_system import Debian, Fedora, Suse
from lisa.util import UnsupportedDistroException, find_group_in_lines


class Dhclient(Tool):
    # timeout 300;
    _debian_pattern = re.compile(r"^(?P<default>#?)timeout (?P<number>\d+);$")
    # ipv4.dhcp-timeout=300
    _fedora_pattern = re.compile(r"^ipv4\.dhcp-timeout=+(?P<number>\d+)$")

    @property
    def command(self) -> str:
        return "dhclient"

    @classmethod
    def _freebsd_tool(cls) -> Optional[Type[Tool]]:
        return DhclientFreeBSD

    @property
    def can_install(self) -> bool:
        return False

    def get_timeout(self) -> int:
        is_default_value: bool = True
        if isinstance(self.node.os, Debian) or isinstance(self.node.os, Suse):
            if isinstance(self.node.os, Debian):
                path = "/etc/dhcp/dhclient.conf"
            else:
                path = "/etc/dhclient.conf"
            # the default value in debian is 300
            value: int = 300
            cat = self.node.tools[Cat]
            output = cat.read(path)
            group = find_group_in_lines(output, self._debian_pattern)
            if group and not group["default"]:
                value = int(group["number"])
                is_default_value = False
        elif isinstance(self.node.os, Fedora):
            # the default value in fedora is 45
            value = 45
            result = self.node.execute("NetworkManager --print-config", sudo=True)
            group = find_group_in_lines(result.stdout, self._fedora_pattern)
            if group and value != int(group["number"]):
                value = int(group["number"])
                is_default_value = False
        else:
            raise UnsupportedDistroException(os=self.node.os)

        self._log.debug(f"timeout value: {value}, is default: {is_default_value}")

        return value

    def renew(self, interface: str = "") -> None:
        if interface:
            result = self.run(
                f"-r {interface} && dhclient {interface}",
                shell=True,
                sudo=True,
                force_run=True,
            )
        else:
            result = self.run(
                "-r && dhclient",
                shell=True,
                sudo=True,
                force_run=True,
            )
        result.assert_exit_code(
            0, f"dhclient renew return non-zero exit code: {result.stdout}"
        )


class DhclientFreeBSD(Dhclient):
    @property
    def command(self) -> str:
        return "dhclient"

    def renew(self, interface: str = "") -> None:
        interface = interface or ""
        self.run(
            interface,
            shell=True,
            sudo=True,
            force_run=True,
            expected_exit_code=0,
            expected_exit_code_failure_message="unable to renew ip address",
        )
