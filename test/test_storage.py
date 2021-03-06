from datetime import datetime
from io import BytesIO
from pathlib import Path
from rohmu import errors

import pytest


@pytest.mark.parametrize("transfer", ["local_transfer"])
def test_nonexistent(transfer, request):
    transfer = request.getfixturevalue(transfer)
    with pytest.raises(errors.FileNotFoundFromStorageError):
        transfer.get_metadata_for_key("NONEXISTENT")
    with pytest.raises(errors.FileNotFoundFromStorageError):
        transfer.delete_key("NONEXISTENT")
    with pytest.raises(errors.FileNotFoundFromStorageError):
        transfer.get_contents_to_file("NONEXISTENT", "nonexistent/a")
    with pytest.raises(errors.FileNotFoundFromStorageError):
        transfer.get_contents_to_fileobj("NONEXISTENT", BytesIO())
    with pytest.raises(errors.FileNotFoundFromStorageError):
        transfer.get_contents_to_string("NONEXISTENT")
    assert transfer.list_path("") == []
    assert transfer.list_path("NONEXISTENT") == []


@pytest.mark.parametrize("transfer", ["local_transfer"])
def test_basic_upload(transfer, tmp_path, request):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    transfer = request.getfixturevalue(transfer)
    transfer.store_file_from_memory("x1", b"dummy", {"k": "v"})
    assert transfer.get_contents_to_string("x1") == (b"dummy", {"k": "v"})
    # Same thing, but with a key looking like a directory
    transfer.store_file_from_memory("NONEXISTENT-DIR/x1", b"dummy", None)
    assert transfer.get_contents_to_string("NONEXISTENT-DIR/x1") == (b"dummy", {})

    # Same thing, but from disk now
    dummy_file = scratch / "a"
    with open(dummy_file, "wb") as fp:
        fp.write(b"dummy")
    transfer.store_file_from_disk("test1/x1", dummy_file, None)
    out = BytesIO()

    assert transfer.get_contents_to_fileobj("test1/x1", out) == {}
    assert out.getvalue() == b"dummy"


@pytest.mark.parametrize("transfer", ["local_transfer"])
def test_copy(transfer, request):
    transfer = request.getfixturevalue(transfer)
    transfer.store_file_from_memory("dummy", b"dummy", {"k": "v"})
    transfer.copy_file(source_key="dummy", destination_key="dummy_copy")
    assert transfer.get_contents_to_string("dummy_copy") == (b"dummy", {"k": "v"})
    # Same thing, but with different metadata
    transfer.copy_file(source_key="dummy", destination_key="dummy_copy_metadata", metadata={"new_k": "new_v"})
    assert transfer.get_contents_to_string("dummy_copy_metadata") == (b"dummy", {"new_k": "new_v"})


@pytest.mark.parametrize("transfer", ["local_transfer"])
def test_list(transfer, request):
    transfer = request.getfixturevalue(transfer)
    assert transfer.list_path("") == []

    # Test with a single file at root
    transfer.store_file_from_memory("dummy", b"dummy", metadata={"k": "v"})
    file_list = transfer.list_path("")
    assert len(file_list) == 1
    assert file_list[0]["name"] == "dummy"
    assert file_list[0]["metadata"] == {"k": "v"}
    assert file_list[0]["size"] == len("dummy")
    assert isinstance(file_list[0]["last_modified"], datetime)

    # Test with a "subdirectory"
    transfer.store_file_from_memory("dummydir/dummy", b"dummy", metadata={"k": "v"})
    assert len(transfer.list_path("")) == 1
    assert set(transfer.iter_prefixes("")) == {"dummydir"}
    assert len(transfer.list_path("dummydir")) == 1

    files = transfer.list_path("", deep=True)
    assert len(files) == 2
    assert set(f["name"] for f in files) == {"dummy", "dummydir/dummy"}


def test_hidden_local_files(local_transfer):
    """
    Local storage specific test.
    """
    storage_dir = Path(local_transfer.prefix)
    # Since we've never used the local storage, need to create the directory
    storage_dir.mkdir()
    # When creating the file manually, we need to create some metadata too.
    with open(Path(local_transfer.prefix) / ".null", "w"):
        pass
    with open(Path(local_transfer.prefix) / ".null.metadata", "w") as f:
        f.write('{"k": "v"}')
    assert local_transfer.list_path("") == []

    # Make sure the previous test actually worked, by manually creating a file
    # that must appear.
    with open(Path(local_transfer.prefix) / "somefile", "w"):
        pass
    with open(Path(local_transfer.prefix) / "somefile.metadata", "w") as f:
        f.write('{"k": "v"}')

    files = local_transfer.list_path("")
    assert len(files) == 1
    assert files[0]["name"] == "somefile"
