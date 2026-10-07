"""
Unit tests: Admin.emb.resolve_chroma_dir
ที่เก็บ ChromaDB ต้องตั้งได้จาก CHROMA_DB_DIR (ไม่ hardcode path ของเครื่องใดเครื่องหนึ่ง)
"""
import os

from Admin import emb


def test_env_var_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMA_DB_DIR", str(tmp_path / "vec"))
    assert emb.resolve_chroma_dir(str(tmp_path)) == str(tmp_path / "vec")


def test_reads_backend_env_file_when_no_env_var(monkeypatch, tmp_path):
    monkeypatch.delenv("CHROMA_DB_DIR", raising=False)
    fake_root = tmp_path / "repo"
    (fake_root / "Admin").mkdir(parents=True)
    (fake_root / "Backend").mkdir()
    (fake_root / "Backend" / ".env").write_text("CHROMA_DB_DIR=D:/vectors/chroma\n", encoding="utf-8")
    monkeypatch.setattr(emb, "__file__", str(fake_root / "Admin" / "emb.py"))
    assert emb.resolve_chroma_dir("ignored") == "D:/vectors/chroma"


def test_defaults_to_index_dir_without_any_setting(monkeypatch, tmp_path):
    monkeypatch.delenv("CHROMA_DB_DIR", raising=False)
    (tmp_path / "Admin").mkdir()
    monkeypatch.setattr(emb, "__file__", str(tmp_path / "Admin" / "emb.py"))  # ไม่มี Backend/.env
    assert emb.resolve_chroma_dir(str(tmp_path / "index_db")) == os.path.join(str(tmp_path / "index_db"), "chroma_db")


def test_no_hardcoded_machine_path_left():
    src = open(emb.__file__, encoding="utf-8").read()
    assert "C:\\\\Users\\\\ITS" not in src and "C:\\Users\\ITS" not in src
