"""OpenMetadata integration via direct REST API."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from pybreaker import CircuitBreaker

from backend.core.config import settings

logger = logging.getLogger(__name__)

_OM_FILE_FORMAT_MAP: Dict[str, str] = {
    "zip": "zip", "gz": "gz", "gzip": "gz", "zstd": "zstd", "zst": "zstd",
    "csv": "csv", "tsv": "tsv", "json": "json", "parquet": "parquet", "avro": "avro",
}


def _to_om_file_formats(extension: str) -> List[str]:
    fmt = _OM_FILE_FORMAT_MAP.get(extension.lower())
    return [fmt] if fmt else []


class _OMRestClient:
    def __init__(self, host: str, token: str, timeout: float = 30.0) -> None:
        base = host.rstrip("/")
        if not base.endswith("/api/v1"):
            base = f"{base}/api/v1"
        self.base = base
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._timeout = timeout

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base}{path}"
        with httpx.Client(timeout=self._timeout) as client:
            r = client.get(url, headers=self._headers, params=params)
            r.raise_for_status()
            return r.json()

    def _put(self, path: str, body: Dict) -> Dict:
        url = f"{self.base}{path}"
        with httpx.Client(timeout=self._timeout) as client:
            r = client.put(url, headers=self._headers, json=body)
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error("PUT %s failed %s: %s", path, e.response.status_code, e.response.text[:500])
                raise
            return r.json()

    def _patch(self, path: str, body: List[Dict]) -> Dict:
        url = f"{self.base}{path}"
        patch_headers = {**self._headers, "Content-Type": "application/json-patch+json"}
        with httpx.Client(timeout=self._timeout) as client:
            r = client.patch(url, headers=patch_headers, json=body)
            r.raise_for_status()
            return r.json()

    def health_check(self) -> bool:
        try:
            self._get("/system/config/jwks")
            return True
        except Exception:
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    r = client.get(
                        f"{self.base.replace('/api/v1', '')}/healthcheck",
                        timeout=self._timeout,
                    )
                    return r.status_code == 200
            except Exception:
                return False

    def get_storage_service(self, name: str) -> Optional[Dict]:
        try:
            return self._get(f"/services/storageServices/name/{name}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_storage_service(self, name: str, description: str) -> Dict:
        body = {
            "name": name,
            "serviceType": "CustomStorage",
            "description": description,
            "connection": {"config": {"type": "CustomStorage"}},
        }
        return self._put("/services/storageServices", body)

    def get_storage_service_id(self, name: str) -> Optional[str]:
        svc = self.get_storage_service(name)
        return svc.get("id") if svc else None

    def get_container(self, fqn: str) -> Optional[Dict]:
        try:
            return self._get(f"/containers/name/{fqn}", params={"fields": "tags,extension"})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_or_update_container(
        self,
        name: str,
        service_name: str,
        file_formats: List[str],
        size: int,
        full_path: str,
        description: str = "",
    ) -> Dict:
        body: Dict[str, Any] = {
            "name": name,
            "service": service_name,
            "sourceUrl": full_path,
            "description": description,
        }
        if file_formats:
            body["fileFormats"] = file_formats
        if size:
            body["size"] = size
        return self._put("/containers", body)

    def patch_container_tags(self, container_id: str, tag_fqns: List[str]) -> Dict:
        patch = [
            {
                "op": "add",
                "path": "/tags/-",
                "value": {
                    "tagFQN": fqn,
                    "source": "Classification",
                    "labelType": "Manual",
                    "state": "Confirmed",
                },
            }
            for fqn in tag_fqns
        ]
        return self._patch(f"/containers/{container_id}", patch)

    def add_lineage(
        self,
        from_id: str,
        from_type: str,
        to_id: str,
        to_type: str,
        description: str = "",
    ) -> Dict:
        body = {
            "edge": {
                "fromEntity": {"id": from_id, "type": from_type},
                "toEntity": {"id": to_id, "type": to_type},
                "lineageDetails": {"description": description},
            }
        }
        return self._put("/lineage", body)

    def get_policy(self, name: str) -> Optional[Dict]:
        try:
            return self._get(f"/policies/name/{name}", params={"include": "all"})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def create_or_update_policy(self, body: Dict) -> Dict:
        try:
            return self._put("/policies", body)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                return self._get(
                    f"/policies/name/{body.get('name', '')}",
                    params={"include": "all"},
                )
            raise

    def get_role(self, fqn: str) -> Optional[Dict]:
        try:
            return self._get(f"/roles/name/{fqn}", params={"fields": "policies"})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def patch_role_policies(self, role_id: str, policy_id: str) -> Dict:
        patch = [{"op": "add", "path": "/policies/-", "value": {"id": policy_id, "type": "policy"}}]
        return self._patch(f"/roles/{role_id}", patch)

    def get_type_id(self, type_name: str) -> Optional[str]:
        try:
            result = self._get(f"/metadata/types/name/{type_name}")
            return result.get("id")
        except Exception:
            return None

    def register_custom_property(
        self,
        entity_type_id: str,
        prop_name: str,
        prop_type_id: str,
        prop_type_name: str,
        description: str,
    ) -> None:
        body = {
            "name": prop_name,
            "description": description,
            "propertyType": {
                "id": prop_type_id,
                "type": "type",
                "name": prop_type_name,
                "fullyQualifiedName": prop_type_name,
            },
        }
        try:
            self._put(f"/metadata/types/{entity_type_id}", body)
            logger.info("Custom property registered: %s", prop_name)
        except httpx.HTTPStatusError as e:
            if "already exists" in e.response.text.lower() or e.response.status_code in (400, 409):
                logger.debug("Custom property already exists: %s", prop_name)
            else:
                logger.warning(
                    "Custom property registration issue for %s [%s]: %s",
                    prop_name, e.response.status_code, e.response.text[:200],
                )

    def ensure_ingestion_pipeline(self, service_name: str, pipeline_name: str) -> str:
        svc = self.get_storage_service(service_name)
        if not svc:
            raise RuntimeError(f"Storage service '{service_name}' not found")
        body = {
            "name": pipeline_name,
            "displayName": "Morolo PII Redaction Pipeline",
            "description": (
                "Scans uploaded documents for Indian Government ID PII (Aadhaar, PAN, DL), "
                "scores risk, performs redaction, and registers assets in OpenMetadata."
            ),
            "pipelineType": "application",
            "service": {"id": svc["id"], "type": "storageService"},
            "airflowConfig": {"scheduleInterval": None},
            "sourceConfig": {"config": {}},
        }
        try:
            result = self._put("/services/ingestionPipelines", body)
            return result.get("fullyQualifiedName", f"{service_name}.{pipeline_name}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                fqn = f"{service_name}.{pipeline_name}"
                try:
                    existing = self._get(f"/services/ingestionPipelines/name/{fqn}")
                    return existing.get("fullyQualifiedName", fqn)
                except Exception:
                    return fqn
            raise

    def put_pipeline_status(
        self,
        pipeline_fqn: str,
        run_id: str,
        state: str,
        start_ms: int,
        end_ms: int,
        docs_ok: int,
        docs_failed: int,
    ) -> None:
        import time
        from urllib.parse import quote
        payload = {
            "runId": run_id,
            "pipelineState": state,
            "startDate": start_ms,
            "timestamp": int(time.time() * 1000),
            "endDate": end_ms,
            "status": {
                "records": docs_ok,
                "failures": docs_failed,
                "warnings": 0,
                "filtered": 0,
            },
        }
        encoded = quote(pipeline_fqn, safe="")
        url = f"{self.base}/services/ingestionPipelines/name/{encoded}/pipelineStatus"
        with httpx.Client(timeout=self._timeout) as client:
            r = client.put(url, headers=self._headers, json=payload)
            if r.status_code not in (200, 201):
                logger.warning("pipelineStatus PUT failed [%s]: %s", r.status_code, r.text[:200])


class OMIntegrationService:
    STORAGE_SERVICE_NAME = "morolo-docs"

    # Updated to use MoroloPII classification created in OM UI
    _TAG_MAP = {
        "AADHAAR":         "MoroloPII.Sensitive.IndianGovtID.Aadhaar",
        "PAN":             "MoroloPII.Sensitive.IndianGovtID.PAN",
        "DRIVING_LICENSE": "MoroloPII.Sensitive.IndianGovtID.DrivingLicense",
        "EMAIL_ADDRESS":   "MoroloPII.Sensitive.ContactInfo.Email",
        "PHONE_NUMBER":    "MoroloPII.Sensitive.ContactInfo.Phone",
        "PERSON":          "MoroloPII.Sensitive",
    }

    def __init__(self) -> None:
        self._client: Optional[_OMRestClient] = None
        self.dpdp_policy_id: Optional[str] = None
        self._pipeline_fqn: Optional[str] = None

        self.circuit_breaker = CircuitBreaker(
            fail_max=settings.CIRCUIT_BREAKER_FAIL_MAX,
            reset_timeout=settings.CIRCUIT_BREAKER_RESET_TIMEOUT,
            name="OM_REST_API",
        )

        if not settings.OM_TOKEN:
            logger.warning("OMIntegrationService: OM_TOKEN not set — stub mode")
            return
        if not settings.OM_HOST:
            logger.warning("OMIntegrationService: OM_HOST not set — stub mode")
            return

        try:
            client = _OMRestClient(host=settings.OM_HOST, token=settings.OM_TOKEN)
            if client.health_check():
                self._client = client
                logger.info("OMIntegrationService: connected to %s", settings.OM_HOST)
            else:
                logger.warning(
                    "OMIntegrationService: OM at %s unreachable — stub mode",
                    settings.OM_HOST,
                )
        except Exception as e:
            logger.warning("OMIntegrationService: init failed (%s) — stub mode", e)

    def _is_available(self) -> bool:
        return self._client is not None

    def _call(self, fn, *args, **kwargs):
        if not self._is_available():
            return None
        try:
            return self.circuit_breaker.call(fn, *args, **kwargs)
        except Exception as e:
            logger.error("OM REST call failed: %s", e)
            return None

    def ensure_storage_service(self) -> str:
        if not self._is_available():
            return self.STORAGE_SERVICE_NAME
        try:
            existing = self._call(self._client.get_storage_service, self.STORAGE_SERVICE_NAME)
            if existing:
                return existing.get("fullyQualifiedName", self.STORAGE_SERVICE_NAME)
            svc = self._call(
                self._client.create_storage_service,
                self.STORAGE_SERVICE_NAME,
                "Morolo document storage for PII governance",
            )
            if svc:
                fqn = svc.get("fullyQualifiedName", self.STORAGE_SERVICE_NAME)
                logger.info("Created storage service: %s", fqn)
                return fqn
        except Exception as e:
            logger.error("Failed to ensure storage service: %s", e)
        return self.STORAGE_SERVICE_NAME

    def ensure_classification_hierarchy(self) -> None:
        # MoroloPII classification already created manually in OM UI
        # Hierarchy:
        #   MoroloPII > Sensitive > IndianGovtID > Aadhaar / PAN / DrivingLicense
        #   MoroloPII > Sensitive > ContactInfo  > Email / Phone
        logger.info("Using MoroloPII classification (pre-configured in OM UI)")

    def bootstrap(self) -> None:
        """Full startup bootstrap — call once when FastAPI starts."""
        if not self._is_available():
            logger.warning("OM not available — skipping bootstrap")
            return
        logger.info("=== Morolo OM Bootstrap starting ===")
        self.ensure_storage_service()
        self.bootstrap_custom_properties()
        self.ensure_pipeline()
        logger.info("=== Morolo OM Bootstrap complete ===")

    def bootstrap_custom_properties(self) -> None:
        """Register Morolo custom properties on the Container entity type."""
        if not self._is_available():
            return
        try:
            container_type = self._client._get("/metadata/types/name/container")
            container_type_id = container_type.get("id")
            if not container_type_id:
                logger.warning("Could not get Container type ID — skipping custom properties")
                return

            props = [
                ("riskScore",        "number", "Morolo PII risk score (0–100)"),
                ("riskBand",         "string", "Risk band: LOW | MEDIUM | HIGH | CRITICAL"),
                ("detectedPiiTypes", "string", "Comma-separated detected PII entity types"),
                ("redactionLevel",   "string", "Redaction level: light | full | synthetic | none"),
                ("moroloPolicyId",   "string", "DPDP Act OM policy ID applied to this container"),
            ]
            for prop_name, type_name, description in props:
                type_id = self._client.get_type_id(type_name)
                if type_id:
                    self._client.register_custom_property(
                        container_type_id, prop_name, type_id, type_name, description
                    )
            logger.info("Custom properties bootstrapped on Container entity type")
        except Exception as e:
            logger.warning("Custom properties bootstrap failed: %s", e)

    def ensure_pipeline(self) -> None:
        """Register the Morolo IngestionPipeline entity in OM (idempotent)."""
        if not self._is_available():
            return
        try:
            fqn = self._call(
                self._client.ensure_ingestion_pipeline,
                self.STORAGE_SERVICE_NAME,
                "morolo-pii-redaction-pipeline",
            )
            if fqn:
                self._pipeline_fqn = fqn
                logger.info("IngestionPipeline registered: %s", fqn)
        except Exception as e:
            logger.warning("Failed to register pipeline: %s", e)

    def create_container_entity(
        self,
        job_id: str,
        filename: str,
        file_size: int,
        storage_key: str,
        risk_score: float,
        risk_band: str,
        pii_types: List[str],
        is_redacted: bool = False,
    ) -> str:
        container_name = f"{filename}.redacted" if is_redacted else filename
        stub_fqn = f"{self.STORAGE_SERVICE_NAME}.{container_name}"

        if not self._is_available():
            return stub_fqn

        self.ensure_storage_service()

        try:
            raw_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
            file_formats = _to_om_file_formats(raw_ext)
            description = (
                f"{'[REDACTED VERSION] ' if is_redacted else ''}"
                f"Risk: {risk_band} ({risk_score:.1f}/100) | "
                f"PII detected: {', '.join(pii_types) if pii_types else 'none'} | "
                f"Managed by Morolo PII Governance | Job: {job_id}"
            )
            result = self._call(
                self._client.create_or_update_container,
                container_name,
                self.STORAGE_SERVICE_NAME,
                file_formats,
                file_size,
                storage_key,
                description,
            )
            if result:
                fqn = result.get("fullyQualifiedName", stub_fqn)
                logger.info("Created Container entity: %s", fqn)
                # Set custom properties
                self.set_risk_properties(
                    container_fqn=fqn,
                    risk_score=risk_score,
                    risk_band=risk_band,
                    pii_types=pii_types,
                    redaction_level="redacted" if is_redacted else "none",
                )
                return fqn
        except Exception as e:
            logger.error("Failed to create Container entity: %s", e)
        return stub_fqn

    def set_risk_properties(
        self,
        container_fqn: str,
        risk_score: float,
        risk_band: str,
        pii_types: List[str],
        redaction_level: str = "none",
        policy_id: Optional[str] = None,
    ) -> None:
        """Set risk custom properties on a container."""
        if not self._is_available():
            return
        extension = {
            "riskScore":        int(round(risk_score)),
            "riskBand":         risk_band,
            "detectedPiiTypes": ", ".join(pii_types) if pii_types else "none",
            "redactionLevel":   redaction_level,
        }
        if policy_id:
            extension["moroloPolicyId"] = policy_id
        try:
            container = self._call(self._client.get_container, container_fqn)
            if not container:
                logger.warning("Container not found for extension: %s", container_fqn)
                return
            container_id = container["id"]
            patch = [{"op": "add", "path": "/extension", "value": extension}]
            self._client._patch(f"/containers/{container_id}", patch)
            logger.info(
                "Custom properties set on %s: risk=%s band=%s",
                container_fqn, risk_score, risk_band,
            )
        except Exception as e:
            logger.warning("Failed to set risk properties on %s: %s", container_fqn, e)

    def apply_tags(self, entity_fqn: str, pii_types: List[str]) -> None:
        if not self._is_available():
            return
        try:
            tag_fqns = [self._TAG_MAP[t] for t in pii_types if t in self._TAG_MAP]
            if not tag_fqns:
                logger.info("No known PII types to tag for %s: %s", entity_fqn, pii_types)
                return
            container = self._call(self._client.get_container, entity_fqn)
            if not container:
                logger.warning("Container not found for tagging: %s", entity_fqn)
                return
            existing_tags = {t.get("tagFQN") for t in (container.get("tags") or [])}
            new_tag_fqns = [fqn for fqn in tag_fqns if fqn not in existing_tags]
            if new_tag_fqns:
                self._call(self._client.patch_container_tags, container["id"], new_tag_fqns)
                logger.info("Applied tags %s to %s", new_tag_fqns, entity_fqn)
            else:
                logger.info("All tags already present on %s", entity_fqn)
        except Exception as e:
            logger.error("Failed to apply tags to %s: %s", entity_fqn, e)

    def create_lineage_edge(
        self,
        original_fqn: str,
        redacted_fqn: str,
        redaction_level: str,
        timestamp: datetime,
    ) -> Optional[str]:
        if not self._is_available():
            return None
        try:
            orig = self._call(self._client.get_container, original_fqn)
            redc = self._call(self._client.get_container, redacted_fqn)
            if not orig:
                logger.warning("Original container not found: %s", original_fqn)
                return None
            if not redc:
                logger.warning("Redacted container not found: %s", redacted_fqn)
                return None
            description = (
                f"Redacted using {redaction_level} strategy "
                f"at {timestamp.isoformat()} by Morolo PII Governance"
            )
            result = self._call(
                self._client.add_lineage,
                orig["id"], "container",
                redc["id"], "container",
                description,
            )
            if result:
                logger.info("Lineage created: %s → %s", original_fqn, redacted_fqn)
                return result.get("id", "created")
        except Exception as e:
            logger.error("Lineage creation failed: %s", e)
        return None

    def register_pipeline_run(self, job_id: str, status: str) -> None:
        import time
        import uuid
        if not self._is_available() or not self._pipeline_fqn:
            logger.info(
                "Pipeline run registered (local): job_id=%s status=%s",
                job_id, status,
            )
            return
        try:
            now_ms = int(time.time() * 1000)
            state = (
                "success" if status == "success"
                else "failed" if status == "failed"
                else "partialSuccess"
            )
            self._client.put_pipeline_status(
                pipeline_fqn=self._pipeline_fqn,
                run_id=str(uuid.uuid4()),
                state=state,
                start_ms=now_ms - 1000,
                end_ms=now_ms,
                docs_ok=1 if state == "success" else 0,
                docs_failed=0 if state == "success" else 1,
            )
            logger.info(
                "Pipeline run logged to OM: job_id=%s state=%s",
                job_id, state,
            )
        except Exception as e:
            logger.warning("Failed to log pipeline run to OM: %s", e)

    def ensure_dpdp_policy(self) -> str:
        if not self._is_available():
            return "stub-policy-id"
        if self.dpdp_policy_id:
            return self.dpdp_policy_id
        policy_name = "DPDP-Act-High-Risk-Document-Masking"
        try:
            existing = self._call(self._client.get_policy, policy_name)
            if existing:
                self.dpdp_policy_id = existing["id"]
                return self.dpdp_policy_id
            policy_body = {
                "name": policy_name,
                "displayName": "DPDP Act High Risk Document Masking Policy",
                "description": (
                    "Masking policy for documents containing Indian Government IDs "
                    "under Digital Personal Data Protection Act 2023"
                ),
                "enabled": True,
                "rules": [
                    {
                        "name": "mask-aadhaar-pan-dl",
                        "effect": "deny",
                        "resources": [f"container:{self.STORAGE_SERVICE_NAME}.*"],
                        "operations": ["ViewAll"],
                    }
                ],
            }
            policy = self._call(self._client.create_or_update_policy, policy_body)
            if not policy:
                return "stub-policy-id"
            self.dpdp_policy_id = policy["id"]
            logger.info("Created DPDP policy: %s", self.dpdp_policy_id)
            try:
                role = self._call(self._client.get_role, "DataConsumer")
                if role:
                    existing_ids = {p["id"] for p in (role.get("policies") or [])}
                    if self.dpdp_policy_id not in existing_ids:
                        self._call(
                            self._client.patch_role_policies,
                            role["id"],
                            self.dpdp_policy_id,
                        )
                        logger.info("DPDP policy assigned to DataConsumer role")
            except Exception as e:
                logger.warning("Could not assign policy to role: %s", e)
            return self.dpdp_policy_id
        except Exception as e:
            logger.error("Failed to create DPDP policy: %s", e)
            return "stub-policy-id"

    def verify_policy_enforcement(self, entity_fqn: str) -> Dict[str, Any]:
        empty = {"has_policy_tags": False, "matching_tags": [], "policy_will_apply": False}
        if not self._is_available():
            return empty
        try:
            container = self._call(self._client.get_container, entity_fqn)
            if not container:
                return empty
            policy_tag_fqns = set(self._TAG_MAP.values())
            matching = [
                t["tagFQN"]
                for t in (container.get("tags") or [])
                if t.get("tagFQN") in policy_tag_fqns
            ]
            return {
                "has_policy_tags": bool(matching),
                "matching_tags": matching,
                "policy_will_apply": bool(matching),
            }
        except Exception as e:
            logger.error("Failed to verify policy enforcement: %s", e)
            return empty