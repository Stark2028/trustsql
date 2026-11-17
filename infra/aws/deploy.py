"""Deploy the explicit low-traffic demo. Credentials stay with AWS CLI; tokens never print."""

import hashlib
import json
import secrets
import subprocess
from pathlib import Path

REGION = "ap-south-1"
STACK = "trustsql-demo"
ROOT = Path("var/aws")


def aws(*args, payload=None):
    command = ["aws", *args, "--region", REGION, "--output", "json", "--no-cli-pager"]
    if payload is not None:
        file = ROOT / "request.json"
        file.write_text(json.dumps(payload), encoding="utf-8")
        command += ["--cli-input-json", f"file://{file.as_posix()}"]
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"AWS {args[0]} {args[1]} failed; check AWS console permissions/status")
    return json.loads(result.stdout or b"{}")


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    identity = aws("sts", "get-caller-identity")
    bucket = f"trustsql-artifacts-{identity['Account']}-{REGION}"
    existing = subprocess.run(
        [
            "aws",
            "s3api",
            "head-bucket",
            "--bucket",
            bucket,
            "--expected-bucket-owner",
            identity["Account"],
            "--region",
            REGION,
        ],
        capture_output=True,
    )
    if existing.returncode:
        aws(
            "s3api",
            "create-bucket",
            "--bucket",
            bucket,
            payload={"CreateBucketConfiguration": {"LocationConstraint": REGION}},
        )
    aws(
        "s3api",
        "put-public-access-block",
        "--bucket",
        bucket,
        payload={
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }
        },
    )
    aws(
        "s3api",
        "put-bucket-tagging",
        "--bucket",
        bucket,
        payload={"Tagging": {"TagSet": [{"Key": "Project", "Value": "TrustSQL"}]}},
    )
    artifact = Path("artifacts/function.zip")
    key = f"releases/{hashlib.sha256(artifact.read_bytes()).hexdigest()}.zip"
    aws("s3api", "put-object", "--bucket", bucket, "--key", key, "--body", str(artifact))
    token_file = ROOT / "api.env"
    if token_file.exists():
        token = token_file.read_text().strip().split("=", 1)[1]
    else:
        token = secrets.token_hex(32)
        token_file.write_text(f"TRUSTSQL_API_TOKEN={token}\n", encoding="utf-8")
    result = aws(
        "cloudformation",
        "create-stack",
        payload={
            "StackName": STACK,
            "TemplateBody": Path("infra/aws/template.json").read_text(),
            "Capabilities": ["CAPABILITY_IAM"],
            "Parameters": [
                {"ParameterKey": "CodeBucket", "ParameterValue": bucket},
                {"ParameterKey": "CodeKey", "ParameterValue": key},
                {"ParameterKey": "ApiToken", "ParameterValue": token},
            ],
            "Tags": [{"Key": "Project", "Value": "TrustSQL"}],
        },
    )
    (ROOT / "deployment.json").write_text(
        json.dumps(
            {"stack": STACK, "region": REGION, "bucket": bucket, "stack_id": result["StackId"]}, indent=2
        )
    )
    print(
        "CloudFormation stack creation started. Owner token saved locally in ignored var/aws/api.env.",
        flush=True,
    )


if __name__ == "__main__":
    main()
