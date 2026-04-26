# Requirements Document

## Introduction

Morolo is a document-level PII detection, redaction, and governance system that extends OpenMetadata to handle unstructured documents (PDFs, images, Word files). The system focuses on detecting Indian government-issued PII (Aadhaar, PAN, Driving License) and integrates with OpenMetadata as a first-class governance extension, providing lineage tracking, custom classification hierarchies, and policy enforcement for document-based sensitive data.

## Glossary

- **Morolo_System**: The complete document PII detection, redaction, and governance system
- **Document_Processor**: Component that extracts text from PDFs, images, and Word documents
- **PII_Detector**: Component that identifies personally identifiable information in extracted text
- **Redaction_Engine**: Component that applies redaction transformations to documents
- **OM_Integration_Service**: Component that manages OpenMetadata API interactions and entity creation
- **Container_Entity**: OpenMetadata entity type used to represent documents (no native Document entity exists)
- **Ingestion_Pipeline**: OpenMetadata's framework for registering custom data processing workflows
- **Lineage_Edge**: OpenMetadata relationship connecting source and derived entities
- **Classification_Tag**: OpenMetadata metadata label for categorizing sensitive data
- **Indian_Govt_ID**: Category including Aadhaar, PAN, and Driving License numbers
- **Light_Redaction**: Partial masking showing first/last characters
- **Full_Redaction**: Complete replacement with black boxes or asterisks
- **Synthetic_Redaction**: Replacement with realistic fake data
- **Risk_Score**: Numerical assessment of PII exposure in a document
- **DPDP_Act**: Digital Personal Data Protection Act (Indian data protection regulation)
- **NextJS_Frontend**: Production web application built with Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, React Query, Framer Motion, and React Flow for document upload, PII visualization, redaction control, and lineage graph display
- **FastAPI_Backend**: REST API service handling document processing requests

## Requirements

### Requirement 1: Document Upload and Text Extraction

**User Story:** As a data governance officer, I want to upload unstructured documents in multiple formats, so that I can analyze them for PII content.

#### Acceptance Criteria

1. WHEN a PDF document with embedded text is uploaded, THE Document_Processor SHALL extract text using pdfminer within 5 seconds for documents under 10MB
2. WHEN an image file (PNG, JPG, JPEG) is uploaded, THE Document_Processor SHALL extract text using Tesseract OCR within 30 seconds for images under 5MB
3. WHEN a Word document (DOCX) is uploaded, THE Document_Processor SHALL extract text using python-docx within 5 seconds for documents under 10MB
4. WHEN a scanned PDF is uploaded, THE Document_Processor SHALL detect the absence of embedded text and apply Tesseract OCR
5. IF text extraction fails, THEN THE Document_Processor SHALL return an error message indicating the failure reason and supported formats
6. THE NextJS_Frontend SHALL accept file uploads with extensions .pdf, .png, .jpg, .jpeg, and .docx

### Requirement 2: Indian Government ID Detection

**User Story:** As a compliance officer, I want to detect Indian government-issued IDs in documents, so that I can ensure DPDP Act compliance.

#### Acceptance Criteria

1. WHEN extracted text contains a 12-digit Aadhaar number pattern, THE PII_Detector SHALL identify it as Indian_Govt_ID with subtype Aadhaar
2. WHEN extracted text contains a 10-character PAN pattern (5 letters, 4 digits, 1 letter), THE PII_Detector SHALL identify it as Indian_Govt_ID with subtype PAN
3. WHEN extracted text contains a Driving License pattern matching state-specific formats, THE PII_Detector SHALL identify it as Indian_Govt_ID with subtype DrivingLicense
4. THE PII_Detector SHALL use Presidio for general PII detection (email, phone, name) in addition to custom Indian_Govt_ID patterns
5. FOR ALL detected PII instances, THE PII_Detector SHALL record the entity type, location (character offset), and confidence score
6. WHEN multiple PII types are detected in a single document, THE Morolo_System SHALL calculate a Risk_Score based on PII type sensitivity and count

### Requirement 3: Gradational Redaction Levels

**User Story:** As a data steward, I want to choose different redaction levels based on use case, so that I can balance data utility with privacy protection.

#### Acceptance Criteria

1. WHERE Light_Redaction is selected, THE Redaction_Engine SHALL mask middle characters while preserving first and last two characters of each PII instance; FOR PII values shorter than 5 characters, THE Redaction_Engine SHALL apply Full_Redaction behavior instead
2. WHERE Full_Redaction is selected, THE Redaction_Engine SHALL replace entire PII instances with black boxes in visual output and asterisks in text
3. WHERE Synthetic_Redaction is selected, THE Redaction_Engine SHALL replace PII instances with realistic fake data matching the original format
4. THE Redaction_Engine SHALL preserve document layout and formatting during redaction operations
5. THE Redaction_Engine SHALL generate both a redacted document file and a redaction metadata report listing all changes
6. WHEN redaction is applied, THE Morolo_System SHALL maintain a mapping between original and redacted content for audit purposes

### Requirement 4: OpenMetadata Container Entity Registration

**User Story:** As a metadata engineer, I want documents registered as Container entities in OpenMetadata, so that they appear in the governance catalog with proper metadata.

#### Acceptance Criteria

1. WHEN a document is uploaded, THE OM_Integration_Service SHALL create a Container_Entity in OpenMetadata representing the original document
2. WHEN a redacted document is generated, THE OM_Integration_Service SHALL create a separate Container_Entity representing the redacted version
3. THE OM_Integration_Service SHALL populate Container_Entity metadata including file name, size, upload timestamp, and document type using the fileFormats field (e.g., ["pdf"]) and the extension field for custom properties
4. BEFORE creating any Container_Entity, THE OM_Integration_Service SHALL ensure a parent StorageService of type CustomStorage named "morolo-docs" is registered in OpenMetadata; all Container FQNs SHALL follow the pattern morolo-docs.{filename}
5. FOR ALL Container_Entity instances, THE OM_Integration_Service SHALL include custom extension properties storing Risk_Score and detected PII types
6. THE OM_Integration_Service SHALL use the OpenMetadata Python SDK (minimum version supporting StorageService entity creation) for all entity creation operations

### Requirement 5: Custom Indian Government ID Classification Hierarchy

**User Story:** As a compliance officer, I want Indian government IDs classified under a custom DPDP-compliant hierarchy, so that I can apply India-specific governance policies.

#### Acceptance Criteria

1. THE OM_Integration_Service SHALL create a custom classification hierarchy: PII.Sensitive.IndianGovtID with subtypes Aadhaar, PAN, and DrivingLicense
2. WHEN an Aadhaar number is detected, THE OM_Integration_Service SHALL apply the PII.Sensitive.IndianGovtID.Aadhaar tag to the Container_Entity
3. WHEN a PAN number is detected, THE OM_Integration_Service SHALL apply the PII.Sensitive.IndianGovtID.PAN tag to the Container_Entity
4. WHEN a Driving License is detected, THE OM_Integration_Service SHALL apply the PII.Sensitive.IndianGovtID.DrivingLicense tag to the Container_Entity
5. THE OM_Integration_Service SHALL register the IndianGovtID classification hierarchy in OpenMetadata before applying tags
6. WHERE general PII (email, phone) is detected, THE OM_Integration_Service SHALL apply standard OpenMetadata PII tags in addition to custom tags

### Requirement 6: Document Lineage Tracking

**User Story:** As a data governance officer, I want to see lineage between original and redacted documents, so that I can track data transformations and audit trails.

#### Acceptance Criteria

1. WHEN a redacted document is created, THE OM_Integration_Service SHALL create a Lineage_Edge from the original Container_Entity to the redacted Container_Entity
2. THE Lineage_Edge SHALL include metadata describing the redaction level applied (Light, Full, or Synthetic)
3. THE Lineage_Edge SHALL include a timestamp of the redaction operation
4. THE OM_Integration_Service SHALL ensure lineage is visible in the OpenMetadata UI lineage graph view
5. WHERE multiple redaction levels are applied to the same document, THE OM_Integration_Service SHALL create separate Lineage_Edge instances for each redacted version
6. THE OM_Integration_Service SHALL use the OpenMetadata addLineage API method for lineage creation

### Requirement 7: Pipeline Run Logging

**User Story:** As a platform engineer, I want Morolo's document processing runs logged as OpenMetadata pipeline run records, so that I can monitor processing history and status.

#### Acceptance Criteria

1. THE OM_Integration_Service SHALL register Morolo as an application pipeline using pipelineType "application" in the OpenMetadata Ingestion Framework
2. WHEN a document is processed, THE OM_Integration_Service SHALL log the operation as a pipeline run record with status (success, failure, partialSuccess)
3. THE pipeline run record SHALL include execution metadata: start time, end time, documents processed, and PII instances detected
4. THE pipeline run records SHALL be visible in the OpenMetadata UI under the registered application pipeline's run history
5. IF document processing fails, THEN THE OM_Integration_Service SHALL log the failure reason in the pipeline run record with status "failed"
6. THE OM_Integration_Service SHALL trigger pipeline run logging via direct OpenMetadata API calls; manual UI triggering is not supported (Airflow is not a dependency)

### Requirement 8: Policy-Based Access Control Integration

**User Story:** As a security administrator, I want to apply OpenMetadata policies to redacted documents, so that I can enforce role-based access restrictions.

#### Acceptance Criteria

1. THE OM_Integration_Service SHALL support applying OpenMetadata masking policies to Container_Entity instances based on Classification_Tag values
2. WHERE a Container_Entity has PII.Sensitive.IndianGovtID tags, THE OM_Integration_Service SHALL recommend masking policies during entity creation
3. THE OM_Integration_Service SHALL support applying access control policies that restrict document visibility based on user roles
4. THE Morolo_System SHALL provide a policy template for DPDP Act compliance that can be imported into OpenMetadata
5. WHEN a policy is applied, THE OM_Integration_Service SHALL record the policy ID in the Container_Entity metadata
6. THE OM_Integration_Service SHALL use the OpenMetadata Policy API for policy application operations

### Requirement 9: Next.js Frontend Application

**User Story:** As a data analyst, I want an intuitive, production-grade web interface to upload documents and control redaction, so that I can use Morolo without technical expertise.

#### Acceptance Criteria

1. THE NextJS_Frontend SHALL provide a drag-and-drop upload zone (UploadDropzone component) accepting .pdf, .png, .jpg, .jpeg, and .docx file formats with client-side file type and size validation before submission
2. WHEN a document is uploaded, THE NextJS_Frontend SHALL poll GET /status/{doc_id} every 3 seconds and display a StatusIndicator reflecting the current pipeline state (PENDING → EXTRACTING → PII_DETECTED → COMPLETED)
3. WHEN PII_DETECTED status is reached, THE NextJS_Frontend SHALL render a DocumentViewer with a PIIHighlighter that overlays color-coded highlights on detected PII spans using character offsets returned by the backend
4. THE NextJS_Frontend SHALL display a RiskScoreCard showing the numeric risk score and risk band (LOW / MEDIUM / HIGH / CRITICAL) with a color-coded visual indicator
5. THE NextJS_Frontend SHALL provide RedactionControls allowing the user to select a redaction level (Light, Full, Synthetic, None) and trigger POST /redact; controls SHALL be disabled while any processing task is in progress
6. WHEN redaction completes, THE NextJS_Frontend SHALL provide download links for the redacted document and the redaction report JSON, and SHALL display a toast notification confirming completion
7. THE NextJS_Frontend SHALL render a LineageGraph component (React Flow) visualizing the directed edge from the original Container entity to the redacted Container entity, with node labels showing entity FQNs
8. THE NextJS_Frontend SHALL display an ActivityTimeline showing a chronological SOC-style log of all pipeline events (upload, extract, detect, redact, ingest) sourced from the audit log endpoint
9. THE NextJS_Frontend SHALL use React Query for all API calls, polling, and client-side caching; skeleton loaders SHALL be shown during data fetching; error boundaries SHALL catch and display structured error messages
10. THE NextJS_Frontend SHALL validate files client-side (extension whitelist, max size) before upload and SHALL never transmit secrets or tokens in URL parameters

### Requirement 10: FastAPI Backend Service

**User Story:** As a system integrator, I want a REST API for document processing, so that I can integrate Morolo with other systems programmatically.

#### Acceptance Criteria

1. THE FastAPI_Backend SHALL expose a POST /upload endpoint accepting multipart file uploads
2. THE FastAPI_Backend SHALL expose a POST /redact endpoint accepting document ID and redaction level parameters
3. THE FastAPI_Backend SHALL expose a GET /status/{document_id} endpoint returning processing status and results
4. THE FastAPI_Backend SHALL expose a GET /risk-score/{document_id} endpoint returning the calculated Risk_Score and detected PII summary
5. THE FastAPI_Backend SHALL return JSON responses with appropriate HTTP status codes (200, 400, 500)
6. THE FastAPI_Backend SHALL implement request validation using Pydantic models
7. THE FastAPI_Backend SHALL handle file storage using a configurable storage backend (local filesystem for hackathon scope)
8. IF an API request fails, THEN THE FastAPI_Backend SHALL return a structured error response with error code and message

### Requirement 11: Configuration and Deployment

**User Story:** As a DevOps engineer, I want Morolo to be configurable and deployable, so that I can run it in different environments.

#### Acceptance Criteria

1. THE Morolo_System SHALL read configuration from environment variables or a config file including OpenMetadata server URL and credentials
2. THE Morolo_System SHALL provide a requirements.txt file listing all Python dependencies with pinned versions
3. THE Morolo_System SHALL provide a README with setup instructions for local development and deployment
4. THE Morolo_System SHALL validate OpenMetadata connectivity on startup and log connection status
5. THE Morolo_System SHALL provide Docker configuration files (Dockerfile, docker-compose.yml) for containerized deployment
6. THE Morolo_System SHALL include sample documents and test cases for demonstration purposes

### Requirement 12: Parser and Pretty Printer for Redaction Metadata

**User Story:** As a compliance auditor, I want to parse and format redaction metadata reports, so that I can analyze redaction operations programmatically.

#### Acceptance Criteria

1. THE Morolo_System SHALL define a RedactionMetadata schema including document ID, PII instances, redaction level, and timestamp
2. THE Morolo_System SHALL provide a Parser that reads RedactionMetadata from JSON format into Python objects using Pydantic v2 model_validate_json()
3. THE Morolo_System SHALL provide a Pretty_Printer that formats RedactionMetadata objects into human-readable JSON using json.dumps(metadata.model_dump(mode="json"), indent=2, sort_keys=True)
4. WHEN invalid RedactionMetadata JSON is provided, THE Parser SHALL return a descriptive error indicating the validation failure
5. FOR ALL valid RedactionMetadata objects, parsing then printing then parsing SHALL produce an equivalent object (round-trip property)
6. THE Pretty_Printer SHALL format JSON with 2-space indentation and sorted keys for consistent output

