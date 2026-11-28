"""Read public links without cookies; HTTP reachability is not proof of free access."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import argparse
import json
import os
from pathlib import Path
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def inspect(url: str) -> dict:
    try:
        request = Request(url, headers={"User-Agent":"Mozilla/5.0 (compatible; JavaRoadmapLinkAudit/1.0)","Accept":"text/html,application/xhtml+xml"})
        with urlopen(request, timeout=15) as response:
            response.read(4096)
            return dict(url=url,final_url=response.url,http_status=response.status,result="reachable")
    except HTTPError as error:
        return dict(url=url,final_url=error.url,http_status=error.code,result="blocked_or_rate_limited" if error.code in (401,403,429) else "http_error")
    except (URLError,TimeoutError,OSError) as error:
        detail=str(error.reason if isinstance(error,URLError) else error)[:180]
        if os.name=="nt" and "CERTIFICATE_VERIFY_FAILED" in detail:
            # Use the Windows HTTP client/trust store, keeping its default TLS
            # validation enabled. URL travels as data in an env var, never code.
            command="$ProgressPreference='SilentlyContinue'; $r=Invoke-WebRequest -UseBasicParsing -Uri $env:JAVA_ROADMAP_AUDIT_URL -TimeoutSec 15 -MaximumRedirection 5; @{status=[int]$r.StatusCode} | ConvertTo-Json -Compress"
            try:
                native=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",command],
                    env={**os.environ,"JAVA_ROADMAP_AUDIT_URL":url},capture_output=True,text=True,timeout=25,
                    creationflags=subprocess.CREATE_NO_WINDOW,shell=False,check=True)
                status=json.loads(native.stdout.strip())["status"]
                return dict(url=url,final_url=url,http_status=status,result="reachable",verification_method="Windows default TLS validation",python_tls_error=detail)
            except (OSError,subprocess.SubprocessError,ValueError,KeyError):
                pass
        return dict(url=url,final_url=None,http_status=None,result="network_unverified",detail=detail)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--retry-unverified",action="store_true",help="Retry pending URLs and inspect new ones, preserving prior successful checks.")
    args=parser.parse_args()
    catalog=json.loads((ROOT/"data/learning/java_backend_v1.json").read_text(encoding="utf-8"))
    urls=sorted({r["url"] for r in catalog["resources"]}|{r["alternative_url"] for r in catalog["resources"] if r.get("alternative_url")}|{c["url"] for c in catalog["courses"]})
    target=ROOT/"docs/JAVA_BACKEND_LINK_AUDIT.json"
    previous={}
    if args.retry_unverified and target.exists():
        old=json.loads(target.read_text(encoding="utf-8"))
        previous={r["url"]:{**r,"checked_at":r.get("checked_at",old["checked_at"])} for r in old["results"] if r["url"] in urls}
    pending=[url for url in urls if not args.retry_unverified or previous.get(url,{}).get("result")!="reachable"]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(inspect,pending):
            previous[result["url"]]={**result,"checked_at":datetime.now(UTC).isoformat()}
    results=[previous[url] for url in urls]
    report=dict(checked_at=datetime.now(UTC).isoformat(),catalog_version=catalog["version"],
        note="HTTP check only, no authentication or paid enrollment; 200 does not prove free access. Blocked/network_unverified links need browser verification, not automatic exclusion.",
        counts=dict(Counter(r["result"] for r in results)),results=results)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report["counts"]))
    for result in results:
        if result["result"]!="reachable":print(json.dumps(result,ensure_ascii=False))
