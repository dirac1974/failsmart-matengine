"""Inter-Team Communication Bus & Cryptographic Audit Logger.

Bridges Division A (Scientific Research Team) and Division B (Scientific Software
Engineering & Redundancy Verification Team), persisting all inter-agent messages,
specifications, redundancy reviews, and test certificates to JSONL logs.
"""

import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class InterTeamBus:
    """Structured message bus and SHA-256 audit logger for the 13-agent team."""

    def __init__(self, logs_dir: str = "/home/antigravity/failsmart-matengine/logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.comm_log_path = self.logs_dir / "inter_team_communication.jsonl"
        self.audit_log_path = self.logs_dir / "verification_audit_log.jsonl"

    def reset_logs(self) -> None:
        if self.comm_log_path.exists():
            self.comm_log_path.unlink()
        if self.audit_log_path.exists():
            self.audit_log_path.unlink()

    @staticmethod
    def compute_sha256(payload: Any) -> str:
        serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def send_inter_team_message(
        self,
        sender_agent: str,
        sender_division: str,
        recipient_agent: str,
        recipient_division: str,
        message_type: str,
        candidate_id: Optional[str],
        subject: str,
        payload: Dict[str, Any],
        model_tier: str = "pro",
    ) -> Dict[str, Any]:
        """Record a formal communication event between Research and Engineering agents."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        digest = self.compute_sha256(payload)
        entry = {
            "timestamp_utc": now_iso,
            "sender_agent": sender_agent,
            "sender_division": sender_division,
            "model_tier": model_tier,
            "recipient_agent": recipient_agent,
            "recipient_division": recipient_division,
            "message_type": message_type,
            "candidate_id": candidate_id,
            "subject": subject,
            "payload_sha256": digest,
            "payload": payload,
        }
        with open(self.comm_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def record_redundancy_verification(
        self,
        verifier_agent: str,
        candidate_id: str,
        formula: str,
        stage_evaluated: int,
        passed_all_checks: bool,
        checks_detail: Dict[str, Any],
        primary_sha256: str,
        independent_sha256: str,
    ) -> Dict[str, Any]:
        """Record an immutable Dual-Redundancy verification event."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record = {
            "timestamp_utc": now_iso,
            "verifier_agent": verifier_agent,
            "candidate_id": candidate_id,
            "formula_reduced": formula,
            "stage_evaluated": stage_evaluated,
            "passed_all_checks": passed_all_checks,
            "primary_sha256": primary_sha256,
            "independent_sha256": independent_sha256,
            "checks": checks_detail,
        }
        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def read_communications(self) -> List[Dict[str, Any]]:
        if not self.comm_log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.comm_log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def read_audit_logs(self) -> List[Dict[str, Any]]:
        if not self.audit_log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.audit_log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
