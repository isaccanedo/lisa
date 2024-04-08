# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import os
from dataclasses import dataclass, field
from pathlib import PurePath, PurePosixPath
from typing import List, Type

from dataclasses_json import dataclass_json

from lisa import schema
from lisa.node import Node
from lisa.tools import Cp, Echo, Ls, Sed, Tar, Uname
from lisa.util import field_metadata

from .kernel_installer import BaseInstaller, BaseInstallerSchema
from .kernel_source_installer import SourceInstaller, SourceInstallerSchema


@dataclass_json()
@dataclass
class BinaryInstallerSchema(BaseInstallerSchema):
    # kernel binary local absolute path
    kernel_image_path: str = field(
        default="",
        metadata=field_metadata(
            required=True,
        ),
    )

    # kernel modules tar.gz files local absolute path
    kernel_modules_path: str = field(
        default="",
        metadata=field_metadata(
            required=True,
        ),
    )

    # initrd binary local absolute path
    initrd_image_path: str = field(
        default="",
        metadata=field_metadata(
            required=False,
        ),
    )


class BinaryInstaller(BaseInstaller):
    @classmethod
    def type_name(cls) -> str:
        return "dom0_binaries"

    @classmethod
    def type_schema(cls) -> Type[schema.TypedSchema]:
        return BinaryInstallerSchema

    @property
    def _output_names(self) -> List[str]:
        return []

    def validate(self) -> None:
        # nothing to validate before source installer started.
        ...

    def install(self) -> str:
        node = self._node
        runbook: BinaryInstallerSchema = self.runbook
        kernel_image_path: str = runbook.kernel_image_path
        initrd_image_path: str = runbook.initrd_image_path
        kernel_modules_path: str = runbook.kernel_modules_path
        is_initrd: bool = False

        uname = node.tools[Uname]
        current_kernel = uname.get_linux_information().kernel_version_raw

        # Kernel absolute path: /home/user/vmlinuz-5.15.57.1+
        # Naming convention : vmlinuz-<version>
        new_kernel = os.path.basename(kernel_image_path).split("-")[1].strip()

        # Copy the binaries to azure VM from where LISA is running
        err: str = f"Can not find kernel image path: {kernel_image_path}"
        assert os.path.exists(kernel_image_path), err
        node.shell.copy(
            PurePath(kernel_image_path),
            node.get_pure_path(f"/var/tmp/vmlinuz-{new_kernel}"),
        )
        _copy_kernel_binary(
            node,
            node.get_pure_path(f"/var/tmp/vmlinuz-{new_kernel}"),
            node.get_pure_path(f"/boot/vmlinuz-{new_kernel}"),
        )

        err = f"Can not find kernel modules path: {kernel_modules_path}"
        assert os.path.exists(kernel_modules_path), err
        node.shell.copy(
            PurePath(kernel_modules_path),
            node.get_pure_path(f"/var/tmp/kernel_modules_{new_kernel}.tar.gz"),
        )
        tar = node.tools[Tar]
        tar.extract(
            file=f"/var/tmp/kernel_modules_{new_kernel}.tar.gz",
            dest_dir="/lib/modules/",
            gzip=True,
            sudo=True,
        )

        if initrd_image_path:
            err = f"Can not find initrd image path: {initrd_image_path}"
            assert os.path.exists(initrd_image_path), err
            is_initrd = True
            node.shell.copy(
                PurePath(initrd_image_path),
                node.get_pure_path(f"/var/tmp/initrd.img-{new_kernel}"),
            )
            _copy_kernel_binary(
                node,
                node.get_pure_path(f"/var/tmp/initrd.img-{new_kernel}"),
                node.get_pure_path(f"/boot/initrd.img-{new_kernel}"),
            )

        _update_mariner_config(
            node,
            is_initrd,
            current_kernel,
            new_kernel,
        )

        return new_kernel


class Dom0Installer(SourceInstaller):
    @classmethod
    def type_name(cls) -> str:
        return "dom0"

    @classmethod
    def type_schema(cls) -> Type[schema.TypedSchema]:
        return SourceInstallerSchema

    @property
    def _output_names(self) -> List[str]:
        return []

    def install(self) -> str:
        node = self._node

        # The /sbin/installkernel script in Mariner expects mariner.cfg to be present.
        # However, the dom0 variant of Mariner doesn't have it. So, `make install`
        # fails. To workaround this failure, create a blank mariner.cfg file. This has
        # no effect on dom0 since this file is not referenced anywhere by dom0 boot.
        # This is only to make the installkernel script happy.
        mariner_cfg = PurePosixPath("/boot/mariner.cfg")
        if not node.tools[Ls].path_exists(str(mariner_cfg), sudo=True):
            node.tools[Echo].write_to_file("", mariner_cfg, sudo=True)

        new_kernel = super().install()

        # If it is dom0,
        # Name of the current kernel binary should be vmlinuz-<kernel version>
        uname = node.tools[Uname]
        current_kernel = uname.get_linux_information().kernel_version_raw

        _update_mariner_config(
            node,
            True,
            current_kernel,
            new_kernel,
        )

        return new_kernel


def _copy_kernel_binary(
    node: Node,
    source: PurePath,
    destination: PurePath,
) -> None:
    cp = node.tools[Cp]
    cp.copy(
        src=source,
        dest=destination,
        sudo=True,
    )


def _update_mariner_config(
    node: Node,
    is_initrd: bool,
    current_kernel: str,
    new_kernel: str,
) -> None:
    mariner_config: str = "/boot/mariner-mshv.cfg"
    sed = node.tools[Sed]

    # Modify the /boot/mariner-mshv.cfg to point new kernel binary
    sed.substitute(
        regexp=f"mariner_linux_mshv=vmlinuz-{current_kernel}",
        replacement=f"mariner_linux_mshv=vmlinuz-{new_kernel}",
        file=mariner_config,
        sudo=True,
    )

    if is_initrd:
        # Modify the /boot/mariner-mshv.cfg to point new initrd binary
        sed.substitute(
            regexp=f"mariner_initrd_mshv=initrd.img-{current_kernel}",
            replacement=f"mariner_initrd_mshv=initrd.img-{new_kernel}",
            file=mariner_config,
            sudo=True,
        )
