import logging
import pytest

from grpc_requests.client import Client, MethodType
from google.protobuf.json_format import ParseError
from google.protobuf.descriptor import MethodDescriptor
import grpc

from tests.common import MetadataClientInterceptor
from tests.test_servers.dependencies import (
    dependencies_pb2,
    dependency1_pb2,
    dependency2_pb2,
)
from google.protobuf import descriptor_pool, descriptor_pb2

"""
Test cases for reflection based client
"""

logger = logging.getLogger("name")


@pytest.fixture(scope="module")
def helloworld_reflection_client():
    try:
        client = Client.get_by_endpoint("localhost:50051")
        yield client
    except:  # noqa: E722
        pytest.fail("Could not connect to local HelloWorld server")


@pytest.fixture(scope="module")
def helloworld_reflection_client_with_interceptor():
    try:
        # Don't use get_by_endpoint here, because interceptors are not cached. Consider caching kwargs too
        client = Client("localhost:50051", interceptors=[MetadataClientInterceptor()])
        yield client
    except:  # noqa: E722
        pytest.fail("Could not connect to local HelloWorld server")


@pytest.fixture(scope="module")
def client_tester_reflection_client():
    try:
        client = Client.get_by_endpoint("localhost:50051")
        yield client
    except:  # noqa: E722
        pytest.fail("Could not connect to local Test server")


def test_metadata_usage(helloworld_reflection_client):
    response = helloworld_reflection_client.request(
        "helloworld.Greeter",
        "SayHello",
        {"name": "sinsky"},
        metadata=[("password", "12345")],
    )
    assert isinstance(response, dict)
    assert response == {"message": "Hello, sinsky, password accepted!"}


def test_interceptor_usage(helloworld_reflection_client_with_interceptor):
    response = helloworld_reflection_client_with_interceptor.request(
        "helloworld.Greeter",
        "SayHello",
        {"name": "sinsky"},
    )
    assert isinstance(response, dict)
    assert response == {"message": "Hello, sinsky, interceptor accepted!"}


def test_methods_meta(helloworld_reflection_client):
    service = helloworld_reflection_client.service("helloworld.Greeter")
    meta = service.methods_meta
    assert meta["HelloEveryone"].method_type == MethodType.STREAM_UNARY


def test_unary_unary(helloworld_reflection_client):
    response = helloworld_reflection_client.request(
        "helloworld.Greeter", "SayHello", {"name": "sinsky"}
    )
    assert isinstance(response, dict)
    assert response == {"message": "Hello, sinsky!"}


def test_describe_method_request(client_tester_reflection_client):
    request_description = client_tester_reflection_client.describe_method_request(
        "client_tester.ClientTester", "TestUnaryUnary"
    )
    expected_request_description = {
        "factor": "INT32",
        "readings": "FLOAT",
        "uuid": "UINT64",
        "sample_flag": "BOOL",
        "request_name": "STRING",
        "extra_data": "BYTES",
    }
    assert (
        request_description == expected_request_description
    ), f"Expected: {expected_request_description}, Actual: {request_description}"


def test_describe_request(client_tester_reflection_client):
    request_description = client_tester_reflection_client.describe_request(
        "client_tester.ClientTester", "TestUnaryUnary"
    )
    expected_request_description = """TestRequest
Fields:
\tfactor: INT32
\treadings: FLOAT
\tuuid: UINT64
\tsample_flag: BOOL
\trequest_name: STRING
\textra_data: BYTES"""
    assert request_description == expected_request_description


def test_describe_response(client_tester_reflection_client):
    request_description = client_tester_reflection_client.describe_response(
        "client_tester.ClientTester", "TestUnaryUnary"
    )
    expected_response_description = """TestResponse
Fields:
\taverage: DOUBLE
\tfeedback: STRING"""
    assert request_description == expected_response_description


def test_empty_body_request(helloworld_reflection_client):
    response = helloworld_reflection_client.request(
        "helloworld.Greeter", "SayHello", {}
    )
    assert isinstance(response, dict)


def test_nonexistent_service(helloworld_reflection_client):
    with pytest.raises(ValueError):
        helloworld_reflection_client.request("helloworld.Speaker", "SingHello", {})


def test_nonexistent_method(helloworld_reflection_client):
    with pytest.raises(ValueError):
        helloworld_reflection_client.request("helloworld.Greeter", "SayGoodbye", {})


def test_unsupported_argument(helloworld_reflection_client):
    with pytest.raises(ParseError):
        helloworld_reflection_client.request(
            "helloworld.Greeter", "SayHello", {"foo": "bar"}
        )


def test_unary_stream(helloworld_reflection_client):
    name_list = ["sinsky", "viridianforge", "jack", "harry"]
    responses = helloworld_reflection_client.request(
        "helloworld.Greeter", "SayHelloGroup", {"name": "".join(name_list)}
    )
    assert all(isinstance(response, dict) for response in responses)
    for response, name in zip(responses, name_list):
        assert response == {"message": f"Hello, {name}!"}


def test_stream_unary(helloworld_reflection_client):
    name_list = ["sinsky", "viridianforge", "jack", "harry"]
    response = helloworld_reflection_client.request(
        "helloworld.Greeter", "HelloEveryone", [{"name": name} for name in name_list]
    )
    assert isinstance(response, dict)
    assert response == {"message": f'Hello, {" ".join(name_list)}!'}


def test_stream_stream(helloworld_reflection_client):
    name_list = ["sinsky", "viridianforge", "jack", "harry"]
    responses = helloworld_reflection_client.request(
        "helloworld.Greeter", "SayHelloOneByOne", [{"name": name} for name in name_list]
    )
    assert all(isinstance(response, dict) for response in responses)
    for response, name in zip(responses, name_list):
        assert response == {"message": f"Hello, {name}!"}


def test_reflection_service_client(helloworld_reflection_client):
    svc_client = helloworld_reflection_client.service("helloworld.Greeter")
    method_names = svc_client.method_names
    assert method_names == (
        "SayHello",
        "SayHelloGroup",
        "HelloEveryone",
        "SayHelloOneByOne",
    )


def test_reflection_service_client_invalid_service(helloworld_reflection_client):
    with pytest.raises(ValueError):
        helloworld_reflection_client.service("helloWorld.Singer")


def test_method_descriptor_on_meta(helloworld_reflection_client):
    method_descriptor = helloworld_reflection_client.get_method_meta(
        "helloworld.Greeter", "SayHello"
    )
    assert isinstance(method_descriptor.descriptor, MethodDescriptor)
    assert method_descriptor.descriptor.name == "SayHello"
    assert method_descriptor.descriptor.containing_service.name == "Greeter"


def test_get_service_descriptor(helloworld_reflection_client):
    service_descriptor = helloworld_reflection_client.get_service_descriptor(
        "helloworld.Greeter"
    )
    assert service_descriptor.name == "Greeter"


def test_get_file_descriptor_by_name(helloworld_reflection_client):
    file_descriptor = helloworld_reflection_client.get_file_descriptor_by_name(
        "helloworld.proto"
    )
    assert file_descriptor.name == "helloworld.proto"
    assert file_descriptor.package == "helloworld"
    assert file_descriptor.syntax == "proto3"


def test_get_file_descriptor_by_symbol(helloworld_reflection_client):
    file_descriptor = helloworld_reflection_client.get_file_descriptor_by_symbol(
        "helloworld.Greeter"
    )
    assert file_descriptor.name == "helloworld.proto"
    assert file_descriptor.package == "helloworld"
    assert file_descriptor.syntax == "proto3"


def test_get_file_descriptors_by_name():
    client = Client("localhost:50053", descriptor_pool=descriptor_pool.DescriptorPool())
    file_descriptor = client.get_file_descriptors_by_name("dependencies.proto")
    assert file_descriptor[0].name == "dependencies.proto"
    assert file_descriptor[1].name == "dependency1.proto"
    assert file_descriptor[2].name == "dependency2.proto"


def test_get_file_descriptors_by_symbol():
    client = Client("localhost:50053", descriptor_pool=descriptor_pool.DescriptorPool())
    file_descriptor = client.get_file_descriptors_by_symbol("dependencies.Greeter")
    assert file_descriptor[0].name == "dependencies.proto"
    assert file_descriptor[1].name == "dependency1.proto"
    assert file_descriptor[2].name == "dependency2.proto"


def test_register_file_descriptors_no_lookup():
    # Connect to not a real server to make sure we do local lookup
    client = Client(
        "localhost:notaport",
        lazy=True,
        descriptor_pool=descriptor_pool.DescriptorPool(),
    )
    descriptors = [
        dependencies_pb2.DESCRIPTOR,
        dependency1_pb2.DESCRIPTOR,
        dependency2_pb2.DESCRIPTOR,
    ]
    file_descriptors = []
    for descriptor in descriptors:
        proto = descriptor_pb2.FileDescriptorProto()
        descriptor.CopyToProto(proto)
        file_descriptors.append(proto)
    client.register_file_descriptors(file_descriptors)


def test_register_file_descriptors_no_lookup_out_of_order():
    # Connect to not a real server to make sure we do local lookup
    client = Client(
        "localhost:notaport",
        lazy=True,
        descriptor_pool=descriptor_pool.DescriptorPool(),
    )
    descriptors = [
        dependency1_pb2.DESCRIPTOR,
        dependency2_pb2.DESCRIPTOR,
        dependencies_pb2.DESCRIPTOR,
    ]
    file_descriptors = []
    for descriptor in descriptors:
        proto = descriptor_pb2.FileDescriptorProto()
        descriptor.CopyToProto(proto)
        file_descriptors.append(proto)
    client.register_file_descriptors(file_descriptors)


def test_register_file_descriptors_incomplete_dependencies():
    # Connect to not a real server to make sure we do local lookup
    client = Client(
        "localhost:notaport",
        lazy=True,
        descriptor_pool=descriptor_pool.DescriptorPool(),
    )
    descriptors = [
        dependencies_pb2.DESCRIPTOR,
        dependency1_pb2.DESCRIPTOR,
    ]
    file_descriptors = []
    for descriptor in descriptors:
        proto = descriptor_pb2.FileDescriptorProto()
        descriptor.CopyToProto(proto)
        file_descriptors.append(proto)
    with pytest.raises(grpc.RpcError):
        client.register_file_descriptors(file_descriptors)
