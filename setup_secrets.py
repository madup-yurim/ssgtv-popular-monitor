"""
service_account.json → .streamlit/secrets.toml 변환 (1회 실행용)
"""
import json
from pathlib import Path

sa = json.loads(Path("service_account.json").read_text(encoding="utf-8"))

lines = ["[gcp_service_account]"]
for k, v in sa.items():
    escaped = str(v).replace("\\", "\\\\").replace('"', '\\"')
    lines.append(f'{k} = "{escaped}"')

toml_content = "\n".join(lines) + "\n"

Path(".streamlit").mkdir(exist_ok=True)
Path(".streamlit/secrets.toml").write_text(toml_content, encoding="utf-8")
print("OK: .streamlit/secrets.toml 생성 완료")
