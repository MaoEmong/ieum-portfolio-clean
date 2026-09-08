"""Prove two explicit teaching mutations are caught, then run the real implementation."""

import argparse
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "target/surefire-reports/TEST-portfolio.boundaries.FaultInjectionDemoTest.xml"
NAMES = {"transientReadMustRemain503", "productionDeveloperAuthenticationMustPreventStartup"}
EXPECTED_FAILURES = {
    "transientReadMustRemain503": "Status expected:<503> but was:<404>",
    "productionDeveloperAuthenticationMustPreventStartup": "production must reject developer authentication",
}


def run(maven, inject):
    if REPORT.exists():
        REPORT.unlink()  # Only this generated report; stale results cannot satisfy the check.
    command = [maven, "--batch-mode", "--no-transfer-progress", "-Dtest=FaultInjectionDemoTest",
               "-Dsample.faultDemo=true", f"-Dsample.injectFault={str(inject).lower()}", "test"]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if not REPORT.exists():
        raise SystemExit("Missing fresh test report: dependency/build/runtime failure is not RED evidence.")
    suite = ET.parse(REPORT).getroot()
    cases = suite.findall("testcase")
    failures = sum(case.find("failure") is not None for case in cases)
    if ({case.attrib["name"] for case in cases} != NAMES
            or suite.attrib.get("errors") != "0" or suite.attrib.get("skipped") != "0"):
        raise SystemExit("Unexpected test identities/errors/skips; refusing to label this demonstration successful.")
    if inject:
        if result.returncode == 0 or failures != 2:
            raise SystemExit("RED expected exactly the two teaching contract failures.")
        for case in cases:
            failure = case.find("failure")
            if (failure.attrib.get("type") != "java.lang.AssertionError"
                    or EXPECTED_FAILURES[case.attrib["name"]] not in failure.attrib.get("message", "")):
                raise SystemExit("RED failed for an unexpected reason.")
        print("RED confirmed: both deliberately injected defects violate the contracts.", flush=True)
    elif result.returncode != 0 or failures != 0:
        raise SystemExit("GREEN failed: the real implementation did not satisfy both contracts.")
    else:
        print("GREEN confirmed: both contracts pass with the real implementation.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maven", default="mvn", help="Installed Maven executable (mvn.cmd on Windows)")
    args = parser.parse_args()
    run(args.maven, True)
    run(args.maven, False)
