"""
AWS Lambda Handler for the VSM Agent Orchestrator.
Entry point for API Gateway HTTP API integration.
Python 3.12 - No external dependencies.
Designed for future Bedrock Agent Action Group compatibility.
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional

from router import (
    Router,
    RequestContext,
    extract_header,
    build_response,
    build_error_response,
    bad_request,
    unauthorized,
    forbidden,
    not_found,
    internal_error,
)
from models.schemas import (
    generate_trace_id,
    generate_correlation_id,
    SprintPlanRequest,
    SprintReviewRequest,
    BacklogRefinementRequest,
    StandupAnalysisRequest,
    DecisionLogRequest,
    AgentQueryRequest,
    AgentInvokeRequest,
    AgentResponse,
    OrchestratorMetadata,
    MCPInvocationTrace,
    MCPType,
    ErrorCode,
)
from models.mock_schemas import (
    CreateMockRequest,
    UpdateMockRequest,
    ListMocksRequest,
    ImportMocksRequest,
    TestMockRequest,
    ListMocksData,
    ImportMocksData,
    TestMockData,
    MockConfigData,
    ClearMocksData,
    ResetHitCountsData,
)
from services.orchestrator import OrchestratorService
from services.mock_store import (
    MockStoreService,
    is_mock_mode_enabled,
    get_mock_table_name,
    get_default_jira_mocks,
    get_default_confluence_mocks,
)


# === Logging Configuration ===

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def configure_structured_logging(trace_id: str, correlation_id: str, tenant_id: str) -> None:
    """Configure structured logging context."""
    # In a real implementation, we would use a structured logging library
    # For now, we'll include context in log messages
    pass


# === Router Setup ===

router = Router(prefix="/v1/agent")


# === Agent Route Handlers ===

def handle_sprint_plan(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/sprint/plan"""
    logger.info(f"[{ctx.trace_id}] Processing sprint plan request for tenant {ctx.tenant_id}")
    
    # Parse and validate request
    request = SprintPlanRequest.from_dict(ctx.body or {})
    validation_errors = request.validate()
    
    if validation_errors:
        return bad_request(
            "Invalid request body",
            ctx.trace_id,
            {"validationErrors": validation_errors}
        )
    
    # Execute orchestration
    orchestrator = OrchestratorService(ctx.tenant_id)
    data, metadata = orchestrator.plan_sprint(request)
    
    # Build response
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=metadata,
        data=data
    )
    
    logger.info(f"[{ctx.trace_id}] Sprint plan completed: {data.sprint_id}")
    return build_response(200, response.to_dict())


def handle_sprint_review(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/sprint/review"""
    logger.info(f"[{ctx.trace_id}] Processing sprint review request for tenant {ctx.tenant_id}")
    
    # Parse and validate request
    request = SprintReviewRequest.from_dict(ctx.body or {})
    validation_errors = request.validate()
    
    if validation_errors:
        return bad_request(
            "Invalid request body",
            ctx.trace_id,
            {"validationErrors": validation_errors}
        )
    
    # Execute orchestration
    orchestrator = OrchestratorService(ctx.tenant_id)
    data, metadata = orchestrator.review_sprint(request)
    
    # Build response
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=metadata,
        data=data
    )
    
    logger.info(f"[{ctx.trace_id}] Sprint review completed: {data.sprint_id}")
    return build_response(200, response.to_dict())


def handle_sprint_status(ctx: RequestContext) -> Dict[str, Any]:
    """Handle GET /v1/agent/sprint/{sprintId}/status"""
    sprint_id = ctx.path_params.get("sprintId", "")
    
    if not sprint_id:
        return bad_request("sprintId is required", ctx.trace_id)
    
    logger.info(f"[{ctx.trace_id}] Getting sprint status for {sprint_id}, tenant {ctx.tenant_id}")
    
    # Execute orchestration
    orchestrator = OrchestratorService(ctx.tenant_id)
    data, metadata = orchestrator.get_sprint_status(sprint_id)
    
    # Build response
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=metadata,
        data=data
    )
    
    return build_response(200, response.to_dict())


def handle_backlog_refine(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/backlog/refine"""
    logger.info(f"[{ctx.trace_id}] Processing backlog refinement for tenant {ctx.tenant_id}")
    
    # Parse and validate request
    request = BacklogRefinementRequest.from_dict(ctx.body or {})
    validation_errors = request.validate()
    
    if validation_errors:
        return bad_request(
            "Invalid request body",
            ctx.trace_id,
            {"validationErrors": validation_errors}
        )
    
    # Execute orchestration
    orchestrator = OrchestratorService(ctx.tenant_id)
    data, metadata = orchestrator.refine_backlog(request)
    
    # Build response
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=metadata,
        data=data
    )
    
    logger.info(f"[{ctx.trace_id}] Backlog refinement completed: {len(data.refined_issues)} issues")
    return build_response(200, response.to_dict())


def handle_standup_analyze(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/standup/analyze"""
    logger.info(f"[{ctx.trace_id}] Processing standup analysis for tenant {ctx.tenant_id}")
    
    # Parse and validate request
    request = StandupAnalysisRequest.from_dict(ctx.body or {})
    validation_errors = request.validate()
    
    if validation_errors:
        return bad_request(
            "Invalid request body",
            ctx.trace_id,
            {"validationErrors": validation_errors}
        )
    
    # Execute orchestration
    orchestrator = OrchestratorService(ctx.tenant_id)
    data, metadata = orchestrator.analyze_standup(request)
    
    # Build response
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=metadata,
        data=data
    )
    
    logger.info(f"[{ctx.trace_id}] Standup analysis completed")
    return build_response(200, response.to_dict())


def handle_decision_log_create(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/decision-log/create"""
    logger.info(f"[{ctx.trace_id}] Processing decision log creation for tenant {ctx.tenant_id}")
    
    # Parse and validate request
    request = DecisionLogRequest.from_dict(ctx.body or {})
    validation_errors = request.validate()
    
    if validation_errors:
        return bad_request(
            "Invalid request body",
            ctx.trace_id,
            {"validationErrors": validation_errors}
        )
    
    # Execute orchestration
    orchestrator = OrchestratorService(ctx.tenant_id)
    data, metadata = orchestrator.create_decision_log(request)
    
    # Build response
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=metadata,
        data=data
    )
    
    logger.info(f"[{ctx.trace_id}] Decision log created: {data.decision_id}")
    return build_response(201, response.to_dict())


def handle_agent_query(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/query"""
    logger.info(f"[{ctx.trace_id}] Processing agent query for tenant {ctx.tenant_id}")
    
    # Parse and validate request
    request = AgentQueryRequest.from_dict(ctx.body or {})
    validation_errors = request.validate()
    
    if validation_errors:
        return bad_request(
            "Invalid request body",
            ctx.trace_id,
            {"validationErrors": validation_errors}
        )
    
    # Execute orchestration
    orchestrator = OrchestratorService(ctx.tenant_id)
    data, metadata = orchestrator.process_query(request)
    
    # Build response
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=metadata,
        data=data
    )
    
    logger.info(f"[{ctx.trace_id}] Query processed: {data.query_type.value}")
    return build_response(200, response.to_dict())


def handle_agent_invoke(ctx: RequestContext) -> Dict[str, Any]:
    """
    Handle POST /v1/agent/invoke
    
    Este es el endpoint principal de invocación al agente.
    Recibe un mensaje del usuario y orquesta las consultas/acciones necesarias
    a los MCPs (Jira, Confluence) para generar una respuesta.
    """
    logger.info(f"[{ctx.trace_id}] Processing agent invocation for tenant {ctx.tenant_id}")
    
    # Parse and validate request
    request = AgentInvokeRequest.from_dict(ctx.body or {})
    validation_errors = request.validate()
    
    if validation_errors:
        return bad_request(
            "Invalid request body",
            ctx.trace_id,
            {"validationErrors": validation_errors}
        )
    
    logger.info(f"[{ctx.trace_id}] User message: {request.message[:100]}...")
    
    # Execute agent invocation using the new Agent Core pipeline.
    #
    # NOTE: We keep the response contract compatible with the existing
    # `AgentInvokeData` wrapper so current clients do not break while we
    # evolve the internal arquitectura. Si algo falla en el nuevo
    # pipeline, hacemos fallback transparente al orquestador anterior.
    try:
        from agent_core.pipeline.orchestrator import run_agent_pipeline
        from models.schemas import AgentInvokeData, AgentIntent, DataSource
    except ImportError as e:  # pragma: no cover - defensive fallback
        logger.error(f"[{ctx.trace_id}] Failed to import Agent Core pipeline: {e}")
        orchestrator = OrchestratorService(ctx.tenant_id)
        data, metadata = orchestrator.invoke_agent(request)
        response = AgentResponse(
            trace_id=ctx.trace_id,
            correlation_id=ctx.correlation_id,
            orchestrator_metadata=metadata,
            data=data,
        )
        return build_response(200, response.to_dict())

    try:
        core_ctx = run_agent_pipeline(
            tenant_id=ctx.tenant_id,
            prompt=request.message,
            session_id=request.session_id,
            raw_headers=ctx.headers,
        )

        # Map simple string intent to existing enum where posible
        intent_enum = AgentIntent.UNKNOWN
        intent_map = {
            "create_ticket": AgentIntent.ACTION_PLAN_SPRINT,  # placeholder
            "search_confluence": AgentIntent.QUERY_METRICS,
            "list_backlog": AgentIntent.QUERY_BACKLOG,
        }
        if core_ctx.intent in intent_map:
            intent_enum = intent_map[core_ctx.intent]  # type: ignore[index]

        invoke_data = AgentInvokeData(
            response=core_ctx.final_response_text or "",
            intent=intent_enum,
            intent_confidence=core_ctx.confidence,
            mcp_calls_summary=[],
            actions_taken=[],
            structured_data={"mcpTarget": core_ctx.resolved_mcp_target},
            suggested_followups=[],
            data_sources=[
                DataSource(
                    source_type=core_ctx.resolved_mcp_target or "unknown",
                    reference="agent_core_pipeline",
                )
            ],
            warnings=[],
            session_id=core_ctx.session_id,
        )

        metadata = OrchestratorMetadata(
            mcp_calls=[],
            total_latency_ms=0,
            tenant_id=ctx.tenant_id,
            simulated_confidence_score=core_ctx.confidence,
        )

        response = AgentResponse(
            trace_id=ctx.trace_id,
            correlation_id=ctx.correlation_id,
            orchestrator_metadata=metadata,
            data=invoke_data,
        )

        logger.info(
            f"[{ctx.trace_id}] Agent invocation completed - Intent: {invoke_data.intent.value}, "
            f"Confidence: {invoke_data.intent_confidence:.2f}"
        )
        return build_response(200, response.to_dict())

    except Exception as e:  # pragma: no cover - defensive
        logger.error(f"[{ctx.trace_id}] Agent Core pipeline failed, falling back: {e}")
        import traceback as _tb

        logger.error(_tb.format_exc())

        # Fallback to the previous orchestrator implementation
        orchestrator = OrchestratorService(ctx.tenant_id)
        data, metadata = orchestrator.invoke_agent(request)
        response = AgentResponse(
            trace_id=ctx.trace_id,
            correlation_id=ctx.correlation_id,
            orchestrator_metadata=metadata,
            data=data,
        )
        return build_response(200, response.to_dict())


# === Mock Management Route Handlers ===

def _build_mock_metadata(tenant_id: str) -> OrchestratorMetadata:
    """Build minimal metadata for mock operations."""
    return OrchestratorMetadata(
        mcp_calls=[],
        total_latency_ms=0,
        tenant_id=tenant_id,
        simulated_confidence_score=1.0
    )


def handle_mock_config(ctx: RequestContext) -> Dict[str, Any]:
    """Handle GET /v1/agent/mocks/config - Get mock configuration status"""
    logger.info(f"[{ctx.trace_id}] Getting mock configuration for tenant {ctx.tenant_id}")
    
    mock_store = MockStoreService(ctx.tenant_id)
    all_mocks = mock_store.list_mocks()
    enabled_mocks = mock_store.list_mocks(enabled_only=True)
    jira_mocks = mock_store.list_mocks(mcp_type="jira")
    confluence_mocks = mock_store.list_mocks(mcp_type="confluence")
    
    data = MockConfigData(
        mock_mode_enabled=is_mock_mode_enabled(),
        mock_table_name=get_mock_table_name(),
        total_mocks=len(all_mocks),
        enabled_mocks=len(enabled_mocks),
        jira_mocks=len(jira_mocks),
        confluence_mocks=len(confluence_mocks)
    )
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=data
    )
    
    return build_response(200, response.to_dict())


def handle_list_mocks(ctx: RequestContext) -> Dict[str, Any]:
    """Handle GET /v1/agent/mocks - List all mocks"""
    logger.info(f"[{ctx.trace_id}] Listing mocks for tenant {ctx.tenant_id}")
    
    # Get query params for filtering
    mcp_type = ctx.query_params.get("mcpType")
    operation = ctx.query_params.get("operation")
    enabled_only = ctx.query_params.get("enabledOnly", "").lower() == "true"
    
    mock_store = MockStoreService(ctx.tenant_id)
    all_mocks = mock_store.list_mocks()
    filtered_mocks = mock_store.list_mocks(
        mcp_type=mcp_type,
        operation=operation,
        enabled_only=enabled_only
    )
    
    data = ListMocksData(
        mocks=[m.to_dict() for m in filtered_mocks],
        total_count=len(all_mocks),
        filtered_count=len(filtered_mocks)
    )
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=data
    )
    
    return build_response(200, response.to_dict())


def handle_create_mock(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/mocks - Create a new mock"""
    logger.info(f"[{ctx.trace_id}] Creating mock for tenant {ctx.tenant_id}")
    
    # Parse and validate request
    request = CreateMockRequest.from_dict(ctx.body or {})
    validation_errors = request.validate()
    
    if validation_errors:
        return bad_request(
            "Invalid request body",
            ctx.trace_id,
            {"validationErrors": validation_errors}
        )
    
    mock_store = MockStoreService(ctx.tenant_id)
    created_mock = mock_store.create_mock(request.to_dict(), created_by="api")
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=created_mock
    )
    
    logger.info(f"[{ctx.trace_id}] Mock created: {created_mock.mock_id}")
    return build_response(201, response.to_dict())


def handle_get_mock(ctx: RequestContext) -> Dict[str, Any]:
    """Handle GET /v1/agent/mocks/{mockId} - Get a specific mock"""
    mock_id = ctx.path_params.get("mockId", "")
    
    if not mock_id:
        return bad_request("mockId is required", ctx.trace_id)
    
    logger.info(f"[{ctx.trace_id}] Getting mock {mock_id} for tenant {ctx.tenant_id}")
    
    mock_store = MockStoreService(ctx.tenant_id)
    mock = mock_store.get_mock(mock_id)
    
    if not mock:
        return not_found("Mock", ctx.trace_id, {"mockId": mock_id})
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=mock
    )
    
    return build_response(200, response.to_dict())


def handle_update_mock(ctx: RequestContext) -> Dict[str, Any]:
    """Handle PUT /v1/agent/mocks/{mockId} - Update a mock"""
    mock_id = ctx.path_params.get("mockId", "")
    
    if not mock_id:
        return bad_request("mockId is required", ctx.trace_id)
    
    logger.info(f"[{ctx.trace_id}] Updating mock {mock_id} for tenant {ctx.tenant_id}")
    
    request = UpdateMockRequest.from_dict(ctx.body or {})
    
    mock_store = MockStoreService(ctx.tenant_id)
    updated_mock = mock_store.update_mock(mock_id, request.to_dict())
    
    if not updated_mock:
        return not_found("Mock", ctx.trace_id, {"mockId": mock_id})
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=updated_mock
    )
    
    logger.info(f"[{ctx.trace_id}] Mock updated: {mock_id}")
    return build_response(200, response.to_dict())


def handle_delete_mock(ctx: RequestContext) -> Dict[str, Any]:
    """Handle DELETE /v1/agent/mocks/{mockId} - Delete a mock"""
    mock_id = ctx.path_params.get("mockId", "")
    
    if not mock_id:
        return bad_request("mockId is required", ctx.trace_id)
    
    logger.info(f"[{ctx.trace_id}] Deleting mock {mock_id} for tenant {ctx.tenant_id}")
    
    mock_store = MockStoreService(ctx.tenant_id)
    deleted = mock_store.delete_mock(mock_id)
    
    if not deleted:
        return not_found("Mock", ctx.trace_id, {"mockId": mock_id})
    
    logger.info(f"[{ctx.trace_id}] Mock deleted: {mock_id}")
    return build_response(204, {})


def handle_import_mocks(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/mocks/import - Import multiple mocks"""
    logger.info(f"[{ctx.trace_id}] Importing mocks for tenant {ctx.tenant_id}")
    
    request = ImportMocksRequest.from_dict(ctx.body or {})
    validation_errors = request.validate()
    
    if validation_errors:
        return bad_request(
            "Invalid request body",
            ctx.trace_id,
            {"validationErrors": validation_errors}
        )
    
    mock_store = MockStoreService(ctx.tenant_id)
    success, errors = mock_store.import_mocks(request.mocks, created_by="import")
    
    data = ImportMocksData(
        success_count=success,
        error_count=errors,
        total_count=len(request.mocks)
    )
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=data
    )
    
    logger.info(f"[{ctx.trace_id}] Mocks imported: {success} success, {errors} errors")
    return build_response(200, response.to_dict())


def handle_export_mocks(ctx: RequestContext) -> Dict[str, Any]:
    """Handle GET /v1/agent/mocks/export - Export all mocks"""
    logger.info(f"[{ctx.trace_id}] Exporting mocks for tenant {ctx.tenant_id}")
    
    mcp_type = ctx.query_params.get("mcpType")
    
    mock_store = MockStoreService(ctx.tenant_id)
    mocks = mock_store.export_mocks(mcp_type=mcp_type)
    
    data = {"mocks": mocks, "count": len(mocks)}
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=data
    )
    
    return build_response(200, response.to_dict())


def handle_test_mock(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/mocks/test - Test mock matching"""
    logger.info(f"[{ctx.trace_id}] Testing mock matching for tenant {ctx.tenant_id}")
    
    request = TestMockRequest.from_dict(ctx.body or {})
    validation_errors = request.validate()
    
    if validation_errors:
        return bad_request(
            "Invalid request body",
            ctx.trace_id,
            {"validationErrors": validation_errors}
        )
    
    mock_store = MockStoreService(ctx.tenant_id)
    matched_mock = mock_store.find_matching_mock(
        request.mcp_type,
        request.operation,
        request.request_params
    )
    
    if matched_mock:
        data = TestMockData(
            matched=True,
            mock_id=matched_mock.mock_id,
            mock_description=matched_mock.description,
            response_preview=matched_mock.response
        )
    else:
        data = TestMockData(matched=False)
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=data
    )
    
    return build_response(200, response.to_dict())


def handle_clear_mocks(ctx: RequestContext) -> Dict[str, Any]:
    """Handle DELETE /v1/agent/mocks - Clear all mocks"""
    logger.info(f"[{ctx.trace_id}] Clearing all mocks for tenant {ctx.tenant_id}")
    
    # Require confirmation header
    confirm = extract_header(ctx.headers, "x-confirm-delete")
    if confirm != "yes":
        return bad_request(
            "Confirmation required. Set header 'x-confirm-delete: yes'",
            ctx.trace_id
        )
    
    mock_store = MockStoreService(ctx.tenant_id)
    deleted_count = mock_store.clear_all_mocks()
    
    data = ClearMocksData(deleted_count=deleted_count)
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=data
    )
    
    logger.info(f"[{ctx.trace_id}] Cleared {deleted_count} mocks")
    return build_response(200, response.to_dict())


def handle_reset_hit_counts(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/mocks/reset-hits - Reset all hit counts"""
    logger.info(f"[{ctx.trace_id}] Resetting hit counts for tenant {ctx.tenant_id}")
    
    mock_store = MockStoreService(ctx.tenant_id)
    reset_count = mock_store.reset_hit_counts()
    
    data = ResetHitCountsData(reset_count=reset_count)
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=data
    )
    
    logger.info(f"[{ctx.trace_id}] Reset hit counts for {reset_count} mocks")
    return build_response(200, response.to_dict())


def handle_load_defaults(ctx: RequestContext) -> Dict[str, Any]:
    """Handle POST /v1/agent/mocks/load-defaults - Load default mock templates"""
    logger.info(f"[{ctx.trace_id}] Loading default mocks for tenant {ctx.tenant_id}")
    
    mock_store = MockStoreService(ctx.tenant_id)
    
    # Get default mocks
    default_mocks = get_default_jira_mocks() + get_default_confluence_mocks()
    
    success, errors = mock_store.import_mocks(default_mocks, created_by="defaults")
    
    data = ImportMocksData(
        success_count=success,
        error_count=errors,
        total_count=len(default_mocks)
    )
    
    response = AgentResponse(
        trace_id=ctx.trace_id,
        correlation_id=ctx.correlation_id,
        orchestrator_metadata=_build_mock_metadata(ctx.tenant_id),
        data=data
    )
    
    logger.info(f"[{ctx.trace_id}] Default mocks loaded: {success} success, {errors} errors")
    return build_response(200, response.to_dict())


# === Register Agent Routes ===

# Main Agent Invocation Endpoint (Primary Entry Point)
router.add_route("POST", "/invoke", handle_agent_invoke)

# Specific Action Endpoints (MCPs)
router.add_route("POST", "/sprint/plan", handle_sprint_plan)
router.add_route("POST", "/sprint/review", handle_sprint_review)
router.add_route("GET", "/sprint/{sprintId}/status", handle_sprint_status)
router.add_route("POST", "/backlog/refine", handle_backlog_refine)
router.add_route("POST", "/standup/analyze", handle_standup_analyze)
router.add_route("POST", "/decision-log/create", handle_decision_log_create)
router.add_route("POST", "/query", handle_agent_query)

# === Register Mock Management Routes ===

router.add_route("GET", "/mocks/config", handle_mock_config)
router.add_route("GET", "/mocks/export", handle_export_mocks)
router.add_route("POST", "/mocks/import", handle_import_mocks)
router.add_route("POST", "/mocks/test", handle_test_mock)
router.add_route("POST", "/mocks/reset-hits", handle_reset_hit_counts)
router.add_route("POST", "/mocks/load-defaults", handle_load_defaults)
router.add_route("GET", "/mocks", handle_list_mocks)
router.add_route("POST", "/mocks", handle_create_mock)
router.add_route("DELETE", "/mocks", handle_clear_mocks)
router.add_route("GET", "/mocks/{mockId}", handle_get_mock)
router.add_route("PUT", "/mocks/{mockId}", handle_update_mock)
router.add_route("DELETE", "/mocks/{mockId}", handle_delete_mock)


# === Lambda Handler ===

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point.
    
    Handles API Gateway HTTP API v2.0 payload format.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    # Generate trace IDs
    trace_id = generate_trace_id()
    
    # Extract request information
    try:
        # Handle both HTTP API v2.0 and REST API formats
        request_context = event.get("requestContext", {})
        http_info = request_context.get("http", {})
        
        method = http_info.get("method") or event.get("httpMethod", "GET")
        path = http_info.get("path") or event.get("path", "/")
        
        # Normalize path (remove trailing slash except for root)
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        
        # Extract headers (API Gateway normalizes to lowercase)
        headers = event.get("headers", {}) or {}
        
        # Extract query parameters
        query_params = event.get("queryStringParameters", {}) or {}
        
        # Extract correlation ID from headers or generate new one
        correlation_id = extract_header(headers, "x-correlation-id") or generate_correlation_id()
        

         # Handle CORS preflight
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS,PATCH",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "86400"
                },
                "body": ""
            }

        # Extract and validate tenant ID
        tenant_id = extract_header(headers, "x-tenant-id")
        
        if not tenant_id:
            logger.warning(f"[{trace_id}] Missing x-tenant-id header")
            return bad_request(
                "x-tenant-id header is required",
                trace_id,
                {"field": "x-tenant-id"}
            )
        
        # Validate tenant ID format
        if not tenant_id.startswith("tenant-"):
            logger.warning(f"[{trace_id}] Invalid tenant ID format: {tenant_id}")
            return bad_request(
                "Invalid x-tenant-id format. Must start with 'tenant-'",
                trace_id,
                {"field": "x-tenant-id", "provided": tenant_id}
            )
        
        # Parse body
        body = None
        raw_body = event.get("body")
        if raw_body:
            try:
                # Handle base64 encoded body
                if event.get("isBase64Encoded"):
                    import base64
                    raw_body = base64.b64decode(raw_body).decode("utf-8")
                body = json.loads(raw_body)
            except json.JSONDecodeError as e:
                logger.warning(f"[{trace_id}] Invalid JSON body: {e}")
                return bad_request("Invalid JSON body", trace_id, {"parseError": str(e)})
        
        # Configure logging context
        configure_structured_logging(trace_id, correlation_id, tenant_id)
        
        logger.info(f"[{trace_id}] {method} {path} - tenant: {tenant_id}")
        
        # Route the request
        handler, path_params = router.match(method, path)
        
        if not handler:
            logger.warning(f"[{trace_id}] No route found for {method} {path}")
            return build_error_response(
                404,
                "ROUTE_NOT_FOUND",
                f"No route found for {method} {path}",
                trace_id
            )
        
        # Build request context
        ctx = RequestContext(
            method=method,
            path=path,
            headers=headers,
            query_params=query_params,
            path_params=path_params,
            body=body,
            trace_id=trace_id,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            raw_event=event
        )
        
        # Execute handler
        response = handler(ctx)
        
        # Add trace headers to response
        if "headers" not in response:
            response["headers"] = {}
        response["headers"]["x-trace-id"] = trace_id
        response["headers"]["x-correlation-id"] = correlation_id
        
        return response
        
    except Exception as e:
        logger.error(f"[{trace_id}] Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        return internal_error(trace_id, "An unexpected error occurred")


# === Health Check (for testing) ===

def health_check(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Health check endpoint for ALB/ELB health checks.
    """
    return build_response(200, {
        "status": "healthy",
        "service": "vsm-agent-orchestrator",
        "version": "1.0.0",
        "mockModeEnabled": is_mock_mode_enabled()
    })
