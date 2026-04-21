"""
One-off utility (lives in the backend-testing skill, NOT in the project).
Parses a pg_dump --data-only file (dump_data.sql) and splits it into the
layout expected by tests/conftest.py:

  dumps/dump_<table>.json   - one JSON array per table
  dump_data_setup.sql       - all ALTER TABLE ... DISABLE TRIGGER ALL lines
  dump_data_after.sql       - all ALTER TABLE ... ENABLE TRIGGER ALL lines

IMPORTANT: do NOT mirror the whole production database. Tests must run on
the smallest possible fixture set. Dump only the tables needed by the
tests you are writing, and afterwards prune every dump_<table>.json down
to the specific rows those tests reference. Large dumps slow the suite,
leak business data into the repo, and make failures harder to debug.

Usage:
  1. Copy this script into tests/dump_data/ (temporary; do not commit it
     there).
  2. From the source database, dump ONLY the tables you actually need,
     using a narrow -t filter:
       pg_dump -h HOST -U USER -d DB --data-only \\
               -t users -t <another_table> \\
               -f tests/dump_data/dump_data.sql
     The dump must use COPY ... FROM stdin; blocks terminated by \\. lines.
  3. From tests/dump_data/, run:
       python prepare_sample_dump_for_tests.py
  4. Review each generated dumps/dump_<table>.json and TRIM it to the
     rows the tests actually reference (one happy-path row plus any edge
     cases is usually enough).
  5. Delete the source dump_data.sql and this script from tests/dump_data/.
     Only the generated dumps/dump_<table>.json, dump_data_setup.sql and
     dump_data_after.sql are committed.
"""

from collections import defaultdict
import json
import re

table_regex = re.compile(r'^.*?public"\."(?P<table>.*?)"\((?P<columns>.*?)\)')
result = defaultdict(list)
setup_triggers = []
after_triggers = []
with open("dump_data.sql", "r", encoding="utf-8") as f:
    is_data = False
    table = ""
    current_columns: list[str] = []
    for line in f:
        if "ALTER TABLE" in line and "DISABLE TRIGGER ALL" in line:
            setup_triggers.append(line)
            continue
        elif "ALTER TABLE" in line and "ENABLE TRIGGER ALL" in line:
            after_triggers.append(line)
            continue
        elif "COPY" in line:
            matched = table_regex.match(line)
            if matched:
                is_data = True
                table = matched.group("table")
                current_columns = matched.group("columns").replace('"', "").split(",")
            continue
        elif line.startswith("\\."):
            is_data = False
            table = ""
            current_columns = []
            continue
        if is_data:
            values = {}
            for i, value in enumerate(line[:-1].split("\t")):
                values[current_columns[i].strip()] = value
            result[table].append(values)
            continue

for table_name, rows in result.items():
    with open(f"dumps/dump_{table_name}.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

with open("dump_data_setup.sql", "w", encoding="utf-8") as f:
    f.writelines(setup_triggers)
with open("dump_data_after.sql", "w", encoding="utf-8") as f:
    f.writelines(after_triggers)
