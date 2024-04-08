# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from dataclasses import dataclass
from functools import partial
from typing import Any, List, Optional, Type

from lisa import constants, schema
from lisa.environment import EnvironmentSpace
from lisa.operating_system import Linux, OperatingSystem
from lisa.search_space import (
    IntRange,
    RequirementMixin,
    ResultReason,
    SetSpace,
    check,
    generate_min_capability,
)
from lisa.testsuite import (
    DEFAULT_REQUIREMENT,
    TestCaseRequirement,
    node_requirement,
    simple_requirement,
)
from selftests.test_search_space import SearchSpaceTestCase


@dataclass
class TestCaseSchema:
    environment: EnvironmentSpace
    platform_type: Optional[SetSpace[Type[schema.Platform]]]
    operating_system: Optional[SetSpace[Type[OperatingSystem]]]


@dataclass
class UtTestCaseRequirement(TestCaseRequirement, RequirementMixin):
    def check(self, capability: Any) -> ResultReason:
        assert isinstance(
            capability, UtTestCaseRequirement
        ), f"actual: {type(capability)}"
        result = ResultReason()
        result.merge(
            check(self.environment, capability.environment),
            name="environment",
        )

        return result

    def _generate_min_capability(self, capability: Any) -> Any:
        assert isinstance(
            capability, UtTestCaseRequirement
        ), f"actual: {type(capability)}"
        environment = generate_min_capability(self.environment, capability.environment)
        platform_type = generate_min_capability(
            self.platform_type, capability.platform_type
        )
        os = generate_min_capability(self.os_type, capability.os_type)
        result = TestCaseSchema(
            environment=environment, platform_type=platform_type, operating_system=os
        )

        return result


def ut_simple_requirement(
    min_count: int = 1,
    supported_platform_type: Optional[List[str]] = None,
    unsupported_platform_type: Optional[List[str]] = None,
    supported_os: Optional[List[Type[OperatingSystem]]] = None,
    unsupported_os: Optional[List[Type[OperatingSystem]]] = None,
) -> UtTestCaseRequirement:
    simple = simple_requirement(
        min_count=min_count,
        supported_platform_type=supported_platform_type,
        unsupported_platform_type=unsupported_platform_type,
        supported_os=supported_os,
        unsupported_os=unsupported_os,
    )
    return UtTestCaseRequirement(
        environment=simple.environment,
        platform_type=simple.platform_type,
        os_type=simple.os_type,
    )


def ut_node_requirement(
    node: schema.NodeSpace,
    supported_platform_type: Optional[List[str]] = None,
    unsupported_platform_type: Optional[List[str]] = None,
    supported_os: Optional[List[Type[OperatingSystem]]] = None,
    unsupported_os: Optional[List[Type[OperatingSystem]]] = None,
) -> UtTestCaseRequirement:
    node_require = node_requirement(
        node,
        supported_platform_type,
        unsupported_platform_type,
        supported_os,
        unsupported_os,
    )
    return UtTestCaseRequirement(
        environment=node_require.environment,
        platform_type=node_require.platform_type,
        os_type=node_require.os_type,
    )


UT_DEFAULT_REQUIREMENT = UtTestCaseRequirement(
    environment=DEFAULT_REQUIREMENT.environment,
    platform_type=DEFAULT_REQUIREMENT.platform_type,
    os_type=SetSpace(is_allow_set=True, items=[Linux]),
)


class RequirementTestCase(SearchSpaceTestCase):
    def test_supported_simple_requirement(self) -> None:
        n1 = schema.NodeSpace()
        n1 = n1.generate_min_capability(n1)
        n4 = schema.load_by_type(
            schema.NodeSpace,
            {"type": constants.ENVIRONMENTS_NODES_REQUIREMENT, "core_count": 4},
        )
        n4 = n4.generate_min_capability(n4)
        n4g1 = schema.load_by_type(
            schema.NodeSpace,
            {
                "type": constants.ENVIRONMENTS_NODES_REQUIREMENT,
                "core_count": 4,
                "gpu_count": 1,
            },
        )
        n4g1 = n4g1.generate_min_capability(n4g1)
        n6 = schema.load_by_type(
            schema.NodeSpace,
            {"type": constants.ENVIRONMENTS_NODES_REQUIREMENT, "core_count": 6},
        )
        n6 = n6.generate_min_capability(n6)
        n6g2 = schema.load_by_type(
            schema.NodeSpace,
            {
                "type": constants.ENVIRONMENTS_NODES_REQUIREMENT,
                "core_count": 6,
                "gpu_count": 2,
            },
        )
        n6g2 = n6g2.generate_min_capability(n6g2)
        n6g1 = schema.load_by_type(
            schema.NodeSpace,
            {
                "type": constants.ENVIRONMENTS_NODES_REQUIREMENT,
                "core_count": 6,
                "gpu_count": 1,
            },
        )
        n6g1 = n6g1.generate_min_capability(n6g1)
        n10 = schema.load_by_type(
            schema.NodeSpace,
            {"type": constants.ENVIRONMENTS_NODES_REQUIREMENT, "core_count": 10},
        )
        n10 = n10.generate_min_capability(n10)

        partial_testcase_schema = partial(
            TestCaseSchema,
            platform_type=None,
            operating_system=SetSpace(is_allow_set=True, items=[Linux]),
        )
        s11 = partial_testcase_schema(environment=EnvironmentSpace())
        s11.environment.nodes = [n1]
        s14 = partial_testcase_schema(environment=EnvironmentSpace())
        s14.environment.nodes = [n4]
        s14g1 = partial_testcase_schema(environment=EnvironmentSpace())
        s14g1.environment.nodes = [n4g1]
        s24 = partial_testcase_schema(environment=EnvironmentSpace())
        s24.environment.nodes = [n4, n4]
        s16 = partial_testcase_schema(environment=EnvironmentSpace())
        s16.environment.nodes = [n6]
        s16g2 = partial_testcase_schema(environment=EnvironmentSpace())
        s16g2.environment.nodes = [n6g2]
        s16g1 = partial_testcase_schema(environment=EnvironmentSpace())
        s16g1.environment.nodes = [n6g1]
        s110 = partial_testcase_schema(environment=EnvironmentSpace())
        s110.environment.nodes = [n10]
        s2i6 = partial_testcase_schema(environment=EnvironmentSpace())
        s2i6.environment.nodes = [n6, n6]
        s266 = partial_testcase_schema(environment=EnvironmentSpace())
        s266.environment.nodes = [n6, n6]
        s2610 = partial_testcase_schema(environment=EnvironmentSpace())
        s2610.environment.nodes = [n6, n10]
        s2106 = partial_testcase_schema(environment=EnvironmentSpace())
        s2106.environment.nodes = [n10, n6]

        self._verify_matrix(
            expected_meet=[
                [True, True, True, True, True, True, True, True, True],
                [True, True, True, True, True, True, True, True, True],
                [True, True, True, True, False, True, True, True, False],
                [False, False, False, False, False, True, True, False, False],
                [True, True, True, True, False, True, True, True, False],
                [True, False, True, False, False, False, False, False, False],
            ],
            expected_min=[
                [s11, s16, s16, s16g2, s110, s16, s16, s16, s110],
                [s11, s16, s16, s16g2, s110, s16, s16, s16, s110],
                [s14, s16, s16, s16g2, False, s16, s16, s16, False],
                [False, False, False, False, False, s2i6, s2i6, False, False],
                [s16, s16, s16, s16g2, False, s16, s16, s16, False],
                [s14g1, False, s16g1, False, False, False, False, False, False],
            ],
            requirements=[
                UT_DEFAULT_REQUIREMENT,
                ut_simple_requirement(supported_os=[Linux]),
                ut_node_requirement(
                    node=schema.NodeSpace(core_count=IntRange(4, 8)),
                    supported_os=[Linux],
                ),
                ut_node_requirement(
                    node=schema.NodeSpace(node_count=2, core_count=IntRange(4, 8)),
                    supported_os=[Linux],
                ),
                UtTestCaseRequirement(
                    environment=EnvironmentSpace(
                        nodes=[schema.NodeSpace(core_count=6, node_count=1)]
                    ),
                    os_type=SetSpace(is_allow_set=True, items=[Linux]),
                ),
                ut_node_requirement(
                    node=schema.NodeSpace(
                        node_count=1, core_count=IntRange(4, 8), gpu_count=1
                    ),
                    supported_os=[Linux],
                ),
            ],
            capabilities=[
                ut_simple_requirement(supported_os=[Linux]),
                UtTestCaseRequirement(
                    environment=EnvironmentSpace(
                        nodes=[
                            schema.NodeSpace(core_count=6, node_count=1, gpu_count=0)
                        ]
                    ),
                    os_type=SetSpace(is_allow_set=True, items=[Linux]),
                ),
                UtTestCaseRequirement(
                    environment=EnvironmentSpace(
                        nodes=[
                            schema.NodeSpace(
                                node_count=1, core_count=6, gpu_count=IntRange(max=2)
                            )
                        ]
                    ),
                    os_type=SetSpace(is_allow_set=True, items=[Linux]),
                ),
                UtTestCaseRequirement(
                    environment=EnvironmentSpace(
                        nodes=[
                            schema.NodeSpace(node_count=1, core_count=6, gpu_count=2)
                        ]
                    ),
                    os_type=SetSpace(is_allow_set=True, items=[Linux]),
                ),
                UtTestCaseRequirement(
                    environment=EnvironmentSpace(
                        nodes=[
                            schema.NodeSpace(core_count=10, node_count=1, gpu_count=0)
                        ]
                    ),
                    os_type=SetSpace(is_allow_set=True, items=[Linux]),
                ),
                UtTestCaseRequirement(
                    environment=EnvironmentSpace(
                        nodes=[
                            schema.NodeSpace(core_count=6, node_count=2, gpu_count=0)
                        ]
                    ),
                    os_type=SetSpace(is_allow_set=True, items=[Linux]),
                ),
                UtTestCaseRequirement(
                    environment=EnvironmentSpace(
                        nodes=[
                            schema.NodeSpace(core_count=6, node_count=1, gpu_count=0),
                            schema.NodeSpace(core_count=6, node_count=1, gpu_count=0),
                        ]
                    ),
                    os_type=SetSpace(is_allow_set=True, items=[Linux]),
                ),
                UtTestCaseRequirement(
                    environment=EnvironmentSpace(
                        nodes=[
                            schema.NodeSpace(core_count=6, node_count=1, gpu_count=0),
                            schema.NodeSpace(core_count=10, node_count=1, gpu_count=0),
                        ]
                    ),
                    os_type=SetSpace(is_allow_set=True, items=[Linux]),
                ),
                UtTestCaseRequirement(
                    environment=EnvironmentSpace(
                        nodes=[
                            schema.NodeSpace(core_count=10, node_count=1, gpu_count=0),
                            schema.NodeSpace(core_count=6, node_count=1, gpu_count=0),
                        ]
                    ),
                    os_type=SetSpace(is_allow_set=True, items=[Linux]),
                ),
            ],
        )
