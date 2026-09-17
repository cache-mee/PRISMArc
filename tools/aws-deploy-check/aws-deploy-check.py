#!/usr/bin/env python3
"""Deterministic, read-only AWS deployment guardrails for the Deploy agent.

Wraps read-only `aws` CLI calls — never creates, modifies or destroys any AWS
resource — so security-critical facts about an AWS deployment target are
checked mechanically instead of asserted by an agent. Each subcommand prints
PASS/FAIL plus the supporting fact and exits 0 only on PASS.

Usage:
  aws-deploy-check identity --expected-account <id> --expected-region <region>
  aws-deploy-check sg-open-check --group-id <sg-id> --port <port>
  aws-deploy-check s3-public-access --bucket <name>
  aws-deploy-check cloudfront-oac --distribution-id <id> --origin-id <origin-id>
  aws-deploy-check --help

Consumer: `.claude/agents/deploy.md`'s AWS deployment lifecycle —
  - `identity` at preflight/target-validation, to stop a deploy from landing
    in the wrong AWS account or region.
  - `sg-open-check` at the pre-deploy security gate and again at post-deploy
    verification, for the EC2 security group (port 8000 and port 22).
  - `s3-public-access` and `cloudfront-oac` at the same two points, for the
    frontend bucket/distribution.

Running the same subcommand again is the intended idempotent re-check, not a
retry — it proves nothing regressed rather than repeating a mutation.

Never prints an AWS credential value; only resource facts already visible to
whoever holds the AWS session used to run it.

EXIT:
  0  PASS
  1  FAIL (finding present)
  2  usage/error (aws CLI missing, call failed, bad args)

@author Samson Paul, samson.paul@experionglobal.com
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib"))
from common import banner, die, require_cmd  # noqa: E402

OPEN_CIDRS = {"0.0.0.0/0", "::/0"}


def _aws(*args, allow_fail=False):
    """Run `aws <args> --output json`. Returns parsed JSON, or None on failure
    when allow_fail=True (a missing config is itself a finding, not a usage
    error). die()s on failure otherwise."""
    require_cmd("aws")
    try:
        result = subprocess.run(["aws", *args, "--output", "json"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as exc:
        die(f"could not run aws CLI: {exc}")
    if result.returncode != 0:
        if allow_fail:
            return None
        die(f"aws {' '.join(args)} failed: {result.stderr.strip()[:400]}")
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        die(f"aws {' '.join(args)} returned non-JSON output")


def cmd_identity(args):
    data = _aws("sts", "get-caller-identity")
    account = data.get("Account")
    region = (os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
              or subprocess.run(["aws", "configure", "get", "region"],
                                 stdout=subprocess.PIPE, text=True).stdout.strip())
    ok = account == args.expected_account and region == args.expected_region
    print(f"account: {account} (expected {args.expected_account})")
    print(f"region: {region or '(unset)'} (expected {args.expected_region})")
    print("PASS identity" if ok else "FAIL identity — account/region mismatch")
    sys.exit(0 if ok else 1)


def cmd_sg_open_check(args):
    data = _aws("ec2", "describe-security-groups", "--group-ids", args.group_id)
    groups = data.get("SecurityGroups", [])
    if not groups:
        die(f"security group {args.group_id} not found")
    findings = []
    for perm in groups[0].get("IpPermissions", []):
        from_port, to_port = perm.get("FromPort"), perm.get("ToPort")
        if from_port is None or to_port is None or not (from_port <= args.port <= to_port):
            continue
        for r in perm.get("IpRanges", []):
            if r.get("CidrIp") in OPEN_CIDRS:
                findings.append(f"port {args.port} open to CidrIp {r.get('CidrIp')}")
        for r in perm.get("Ipv6Ranges", []):
            if r.get("CidrIpv6") in OPEN_CIDRS:
                findings.append(f"port {args.port} open to CidrIpv6 {r.get('CidrIpv6')}")
    if findings:
        for f in findings:
            print(f"FAIL: {f}")
        print(f"FAIL sg-open-check {args.group_id}:{args.port}")
        sys.exit(1)
    print(f"PASS sg-open-check {args.group_id}:{args.port} — not open to 0.0.0.0/0 or ::/0")
    sys.exit(0)


def cmd_s3_public_access(args):
    data = _aws("s3api", "get-public-access-block", "--bucket", args.bucket, allow_fail=True)
    cfg = (data or {}).get("PublicAccessBlockConfiguration", {})
    required = ["BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"]
    missing = [k for k in required if not cfg.get(k)]
    if data is None:
        print(f"FAIL s3-public-access {args.bucket} — no public access block configuration found")
        sys.exit(1)
    if missing:
        print(f"FAIL s3-public-access {args.bucket} — not blocked: {', '.join(missing)}")
        sys.exit(1)
    print(f"PASS s3-public-access {args.bucket} — all public access blocked")
    sys.exit(0)


def cmd_cloudfront_oac(args):
    data = _aws("cloudfront", "get-distribution", "--id", args.distribution_id)
    origins = (data.get("Distribution", {}).get("DistributionConfig", {})
               .get("Origins", {}).get("Items", []))
    match = next((o for o in origins if o.get("Id") == args.origin_id), None)
    if match is None:
        print(f"FAIL cloudfront-oac — origin {args.origin_id} not found on {args.distribution_id}")
        sys.exit(1)
    oac = match.get("OriginAccessControlId") or ""
    oai = (match.get("S3OriginConfig", {}) or {}).get("OriginAccessIdentity") or ""
    if oac and not oai:
        print(f"PASS cloudfront-oac {args.distribution_id}:{args.origin_id} — OAC {oac}")
        sys.exit(0)
    print(f"FAIL cloudfront-oac {args.distribution_id}:{args.origin_id} — "
          f"OriginAccessControlId={oac or '(none)'} OriginAccessIdentity={oai or '(none)'}")
    sys.exit(1)


def build_parser():
    p = argparse.ArgumentParser(prog="aws-deploy-check", add_help=True)
    sub = p.add_subparsers(dest="subcommand", required=True)

    s = sub.add_parser("identity")
    s.add_argument("--expected-account", required=True)
    s.add_argument("--expected-region", required=True)
    s.set_defaults(func=cmd_identity)

    s = sub.add_parser("sg-open-check")
    s.add_argument("--group-id", required=True)
    s.add_argument("--port", required=True, type=int)
    s.set_defaults(func=cmd_sg_open_check)

    s = sub.add_parser("s3-public-access")
    s.add_argument("--bucket", required=True)
    s.set_defaults(func=cmd_s3_public_access)

    s = sub.add_parser("cloudfront-oac")
    s.add_argument("--distribution-id", required=True)
    s.add_argument("--origin-id", required=True)
    s.set_defaults(func=cmd_cloudfront_oac)

    return p


def main():
    banner()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
