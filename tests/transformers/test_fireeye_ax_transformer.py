import pytest

from beagle.constants import HashAlgos
from beagle.nodes import File, Process, Domain, IPAddress
from beagle.transformers.fireeye_ax_transformer import FireEyeAXTransformer


@pytest.fixture
def transformer() -> FireEyeAXTransformer:
    return FireEyeAXTransformer(datasource=None)  # type: ignore


def test_init(transformer):
    assert transformer is not None


def test_not_started(transformer):
    assert transformer.process_events({"mode": "not_started"}) is None


def test_process(transformer):
    input_event = {
        "mode": "started",
        "fid": {"ads": "", "content": 1234},
        "parentname": "C:\\Windows\\explorer.exe",
        "cmdline": '"C:\\Users\\admin\\AppData\\Local\\Temp\\bar.exe"',
        "sha1sum": "123",
        "md5sum": "345",
        "sha256sum": "678",
        "pid": 1700,
        "filesize": 1,
        "event_type": "process",
        "value": "C:\\Users\\admin\\AppData\\Local\\Temp\\bar.exe",
        "timestamp": 18552,
        "ppid": 4668,
    }
    nodes = transformer.transform(input_event)

    assert len(nodes) == 4

    proc: Process = nodes[0]
    proc_file: File = nodes[1]
    parent: Process = nodes[2]
    parent_proc_file: File = nodes[3]

    assert proc in parent.launched
    assert {"timestamp": 18552} in parent.launched[proc]

    assert proc.process_image == proc_file.file_name == "bar.exe"
    assert (
        proc.process_image_path == proc_file.file_path == "C:\\Users\\admin\\AppData\\Local\\Temp"
    )

    assert parent.process_image == "explorer.exe"
    assert parent in parent_proc_file.file_of

    assert proc in proc_file.file_of
    assert proc.process_id == 1700
    assert parent.process_id == 4668

    assert proc.hashes[HashAlgos.SHA1] == "123"
    assert proc.hashes[HashAlgos.MD5] == "345"
    assert proc.hashes[HashAlgos.SHA256] == "678"


def test_dns_event_noanswer(transformer):
    input_event = {
        "mode": "dns_query",
        "protocol_type": "udp",
        "hostname": "foobar",
        "event_type": "network",
        "qtype": "Host Address",
        "processinfo": {
            "imagepath": "C:\\Users\\admin\\AppData\\Local\\Temp\\bar.exe",
            "tainted": True,
            "md5sum": "....",
            "pid": 1700,
        },
        "timestamp": 27648,
    }

    nodes = transformer.transform(input_event)

    assert len(nodes) == 3

    proc: Process = nodes[0]
    proc_file: File = nodes[1]
    domain: Domain = nodes[2]

    assert proc.process_image == proc_file.file_name == "bar.exe"
    assert (
        proc.process_image_path == proc_file.file_path == "C:\\Users\\admin\\AppData\\Local\\Temp"
    )
    assert proc in proc_file.file_of

    assert {"timestamp": 27648} in proc.dns_query_for[domain]


def test_dns_event_answer(transformer):
    input_event = {
        "mode": "dns_query_answer",
        "protocol_type": "udp",
        "hostname": "foobar",
        "ipaddress": "127.0.0.1",
        "event_type": "network",
        "qtype": "Host Address",
        "processinfo": {
            "imagepath": "C:\\Users\\admin\\AppData\\Local\\Temp\\bar.exe",
            "tainted": True,
            "md5sum": "....",
            "pid": 1700,
        },
        "timestamp": 27648,
    }

    nodes = transformer.transform(input_event)

    assert len(nodes) == 4

    proc: Process = nodes[0]
    proc_file: File = nodes[1]
    domain: Domain = nodes[2]
    ip_addr: IPAddress = nodes[3]

    assert proc.process_image == proc_file.file_name == "bar.exe"
    assert (
        proc.process_image_path == proc_file.file_path == "C:\\Users\\admin\\AppData\\Local\\Temp"
    )
    assert proc in proc_file.file_of

    assert {"timestamp": 27648} in proc.dns_query_for[domain]
    assert {"timestamp": 27648} in domain.resolves_to[ip_addr]
    assert ip_addr.ip_address == "127.0.0.1"


def test_conn_event(transformer):
    input_event = {
        "mode": "connect",
        "event_type": "network",
        "protocol_type": "tcp",
        "ipaddress": "199.168.199.123",
        "destination_port": 3333,
        "processinfo": {
            "imagepath": "C:\\Users\\admin\\AppData\\Local\\Temp\\bar.exe",
            "tainted": True,
            "md5sum": "....",
            "pid": 1700,
        },
        "timestamp": 27648,
    }

    nodes = transformer.transform(input_event)

    assert len(nodes) == 3

    proc: Process = nodes[0]
    proc_file: File = nodes[1]
    ip_addr: IPAddress = nodes[2]

    assert proc.process_image == proc_file.file_name == "bar.exe"
    assert (
        proc.process_image_path == proc_file.file_path == "C:\\Users\\admin\\AppData\\Local\\Temp"
    )
    assert proc in proc_file.file_of

    assert ip_addr.ip_address == "199.168.199.123"
    assert {"timestamp": 27648, "port": 3333, "protocol": "tcp"} in proc.connected_to[ip_addr]

