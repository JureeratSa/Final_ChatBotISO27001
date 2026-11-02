"""
ตรวจไฟล์ Alembic migration ว่าแตะเฉพาะตารางของแชทบอท (CI รันทุกครั้ง — รันเองได้)

    python infra/scripts/check_migrations.py

ฐานข้อมูล SQL Server ใช้ร่วมกับระบบอื่น (ตาราง Tbl_* ของหน่วยงานอื่น) — migration ที่ autogenerate
แล้วไม่ได้ตรวจ อาจมี op.drop_table / ALTER ตารางของคนอื่นติดมา สคริปต์นี้ไล่ทุกคำสั่ง op.* ในทุกไฟล์
แล้วล้มทันทีถ้าชื่อตารางไม่อยู่ใน app/models/models.py (หรือเป็นชื่อที่อ่านค่าไม่ได้ เช่นมาจากตัวแปร)
"""
import ast
import re
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[2] / "services" / "api"
VERSIONS_DIR = API_DIR / "alembic" / "versions"

# ตำแหน่งชื่อตารางใน argument ของแต่ละคำสั่ง: (ตำแหน่ง positional, ชื่อ keyword)
OP_TABLE_ARGS = {
    "create_table": [(0, "table_name")],
    "drop_table": [(0, "table_name")],
    "rename_table": [(0, "old_table_name"), (1, "new_table_name")],
    "add_column": [(0, "table_name")],
    "drop_column": [(0, "table_name")],
    "alter_column": [(0, "table_name")],
    "batch_alter_table": [(0, "table_name")],
    "create_index": [(1, "table_name")],
    "drop_index": [(None, "table_name")],
    "create_foreign_key": [(1, "source_table"), (2, "referent_table")],
    "create_unique_constraint": [(1, "table_name")],
    "create_check_constraint": [(1, "table_name")],
    "create_primary_key": [(1, "table_name")],
    "drop_constraint": [(1, "table_name")],
    "create_table_comment": [(0, "table_name")],
    "drop_table_comment": [(0, "table_name")],
}
# batch_op.* อยู่ใน with op.batch_alter_table(<ตารางของเรา>) แล้ว — เหลือตรวจแค่ตารางปลายทางของ FK
BATCH_TABLE_ARGS = {"create_foreign_key": [(1, "referent_table")]}
# ชื่อตารางใน SQL ดิบ (op.execute)
SQL_TABLE_RE = re.compile(r"\b(?:FROM|INTO|UPDATE|TABLE|JOIN|TRUNCATE)\s+\[?(?:dbo\]?\.\[?)?([A-Za-z_][\w]*)", re.I)


def owned_tables() -> set[str]:
    models = (API_DIR / "app" / "models" / "models.py").read_text(encoding="utf-8")
    return set(re.findall(r'__tablename__\s*=\s*"([^"]+)"', models)) | {"alembic_version"}


def check_file(path: Path, owned: set[str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    # ค่าคงที่ระดับไฟล์: NAME = "ตาราง" หรือ NAME = {"ตาราง": ...} / ["ตาราง", ...]
    consts: dict[str, set[str]] = {}
    for n in tree.body:
        if not isinstance(n, ast.Assign):
            continue
        v = n.value
        elts = v.keys if isinstance(v, ast.Dict) else v.elts if isinstance(v, (ast.List, ast.Tuple, ast.Set)) else [v]
        if all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in elts):
            consts.update({t.id: {e.value for e in elts} for t in n.targets if isinstance(t, ast.Name)})
    # ตัวแปรลูป: for table, ... in _TABLES.items() → table มีค่าได้ตามสมาชิกของ _TABLES
    for loop in ast.walk(tree):
        if isinstance(loop, ast.For):
            target = loop.target.elts[0] if isinstance(loop.target, ast.Tuple) else loop.target
            source = next((consts[x.id] for x in ast.walk(loop.iter) if isinstance(x, ast.Name) and x.id in consts), None)
            if isinstance(target, ast.Name) and source is not None:
                consts[target.id] = source
    problems = []

    def values_of(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.Name):
            return consts.get(node.id)
        return None

    def check_name(node, where):
        names = values_of(node)
        if names is None:
            problems.append(f"{where}: อ่านชื่อตารางไม่ได้ ({ast.unparse(node)}) — ใช้ชื่อตารางเป็นข้อความตรงๆ")
        else:
            problems.extend(f"{where}: ตาราง '{name}' ไม่ใช่ของแชทบอท" for name in sorted(names - owned))

    for call in ast.walk(tree):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)):
            continue
        obj, fn = call.func.value.id, call.func.attr
        where = f"{path.name}:{call.lineno} {obj}.{fn}"
        if obj == "op" and fn == "execute":
            sqls = values_of(call.args[0]) if call.args else None
            if sqls is None:
                problems.append(f"{where}: ตรวจ SQL ไม่ได้ — ใช้ข้อความ SQL ตรงๆ")
            else:
                problems += [f"{where}: ตาราง '{t}' ไม่ใช่ของแชทบอท"
                             for sql in sqls for t in SQL_TABLE_RE.findall(sql) if t not in owned]
            continue
        spec = OP_TABLE_ARGS.get(fn) if obj == "op" else BATCH_TABLE_ARGS.get(fn)
        for pos, kw in spec or []:
            node = next((k.value for k in call.keywords if k.arg == kw), None)
            if node is None and pos is not None and pos < len(call.args):
                node = call.args[pos]
            if node is not None:
                check_name(node, where)
    return problems


def main() -> int:
    owned = owned_tables()
    files = sorted(VERSIONS_DIR.glob("*.py"))
    problems = [p for f in files for p in check_file(f, owned)]
    for p in problems:
        print(f"❌ {p}")
    if problems:
        print("\nmigration แตะตารางที่ไม่ใช่ของแชทบอท — ฐานข้อมูลใช้ร่วมกับระบบอื่น ห้ามแตะตารางของคนอื่น")
        return 1
    print(f"✅ migration {len(files)} ไฟล์ แตะเฉพาะตารางของแชทบอท ({', '.join(sorted(owned))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
