"""
Comprehensive test suite for Tiny Backspace API
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient

from main import app
from models import CodeRequest, StreamEvent, StreamEventType
from sse_adapter import SSEAdapter
from agent_orchestrator import AgentOrchestrator
from config import Settings


@pytest.fixture
def test_client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = Settings()
    settings.require_auth = False
    settings.enable_telemetry = False
    return settings


@pytest.fixture
def sse_adapter():
    """Create SSE adapter instance"""
    return SSEAdapter()


class TestModels:
    """Test Pydantic models"""
    
    def test_code_request_valid(self):
        """Test valid code request"""
        request = CodeRequest(
            repo_url="https://github.com/octocat/Hello-World",
            prompt="Add a README file"
        )
        assert request.repo_url == "https://github.com/octocat/Hello-World"
        assert request.prompt == "Add a README file"
    
    def test_code_request_invalid_url(self):
        """Test invalid repository URL"""
        with pytest.raises(ValueError):
            CodeRequest(
                repo_url="https://gitlab.com/user/repo",
                prompt="Add a file"
            )
    
    def test_code_request_empty_prompt(self):
        """Test empty prompt validation"""
        with pytest.raises(ValueError):
            CodeRequest(
                repo_url="https://github.com/user/repo",
                prompt="   "
            )
    
    def test_code_request_long_prompt(self):
        """Test prompt length validation"""
        with pytest.raises(ValueError):
            CodeRequest(
                repo_url="https://github.com/user/repo",
                prompt="x" * 1001
            )
    
    def test_stream_event(self):
        """Test stream event model"""
        event = StreamEvent(
            type="progress",
            data={"stage": "cloning", "message": "Cloning repo"}
        )
        assert event.type == "progress"
        assert event.data["stage"] == "cloning"
        assert event.timestamp is not None


class TestSSEAdapter:
    """Test SSE adapter functionality"""
    
    def test_format_event(self, sse_adapter):
        """Test SSE event formatting"""
        event = StreamEvent(
            type="test",
            data={"message": "Hello"}
        )
        
        formatted = sse_adapter.format_event(event)
        assert formatted.startswith("data: ")
        assert formatted.endswith("\n\n")
        
        # Parse JSON
        json_data = json.loads(formatted[6:-2])
        assert json_data["type"] == "test"
        assert json_data["message"] == "Hello"
        assert "timestamp" in json_data
    
    @pytest.mark.asyncio
    async def test_convert_stream_chunk(self, sse_adapter):
        """Test stream chunk conversion"""
        from streaming_response import StreamChunk, ResponseType
        
        # Test thinking chunk
        chunk = StreamChunk(
            type=ResponseType.THINKING,
            content="Analyzing the code..."
        )
        
        event = await sse_adapter.convert_stream_chunk(chunk)
        assert event.type == StreamEventType.AI_MESSAGE
        assert event.data["thinking"] is True
        assert event.data["message"] == "Analyzing the code..."
    
    @pytest.mark.asyncio
    async def test_create_progress_event(self, sse_adapter):
        """Test progress event creation"""
        event = await sse_adapter.create_progress_event(
            stage="cloning",
            message="Cloning repository",
            percentage=50
        )
        
        assert event.type == StreamEventType.PROGRESS
        assert event.data["stage"] == "cloning"
        assert event.data["message"] == "Cloning repository"
        assert event.data["percentage"] == 50


class TestAPI:
    """Test API endpoints"""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Tiny Backspace API"
        assert "endpoints" in data
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_code_endpoint_invalid_url(self, test_client):
        """Test /api/code with invalid URL"""
        response = test_client.post(
            "/api/code",
            json={
                "repo_url": "not-a-url",
                "prompt": "Add a file"
            }
        )
        assert response.status_code == 422
    
    @patch('agent_orchestrator.AgentOrchestrator.process_request')
    def test_code_endpoint_streaming(self, mock_process, test_client):
        """Test /api/code streaming response"""
        # Mock the agent orchestrator
        async def mock_generator():
            yield StreamEvent(
                type="progress",
                data={"stage": "cloning", "message": "Test"}
            )
            yield StreamEvent(
                type="pr_created",
                data={
                    "pr_url": "https://github.com/test/pr/1",
                    "files_changed": 2
                }
            )
        
        mock_process.return_value = mock_generator()
        
        response = test_client.post(
            "/api/code",
            json={
                "repo_url": "https://github.com/test/repo",
                "prompt": "Add a test file"
            },
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


class TestAgentOrchestrator:
    """Test agent orchestrator"""
    
    @pytest.fixture
    def orchestrator(self, mock_settings):
        """Create orchestrator instance"""
        return AgentOrchestrator(mock_settings)
    
    def test_parse_github_url(self, orchestrator):
        """Test GitHub URL parsing"""
        result = orchestrator._parse_github_url("https://github.com/owner/repo")
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"
        
        # Test with .git suffix
        result = orchestrator._parse_github_url("https://github.com/owner/repo.git")
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"
        
        # Test invalid URL
        with pytest.raises(ValueError):
            orchestrator._parse_github_url("https://gitlab.com/owner/repo")
    
    def test_slugify(self, orchestrator):
        """Test text slugification"""
        assert orchestrator._slugify("Add Hello World") == "add-hello-world"
        assert orchestrator._slugify("Fix bug #123") == "fix-bug-123"
        assert orchestrator._slugify("Update  multiple   spaces") == "update-multiple-spaces"
    
    @pytest.mark.asyncio
    async def test_clone_repository(self, orchestrator):
        """Test repository cloning"""
        mock_sandbox = Mock()
        orchestrator.manager.execute_command = Mock(return_value="Cloned successfully")
        
        result = await orchestrator._clone_repository(
            mock_sandbox,
            "https://github.com/test/repo"
        )
        
        assert result["success"] is True
        assert orchestrator.manager.execute_command.called
    
    @pytest.mark.asyncio
    async def test_process_request_error_handling(self, orchestrator):
        """Test error handling in process_request"""
        # Mock sandbox creation to fail
        orchestrator.manager.create_sandbox = Mock(return_value=None)
        
        events = []
        async for event in orchestrator.process_request(
            request_id="test-123",
            repo_url="https://github.com/test/repo",
            prompt="Test prompt"
        ):
            events.append(event)
        
        # Should have at least one error event
        error_events = [e for e in events if e.type == StreamEventType.ERROR]
        assert len(error_events) > 0
        assert "Failed to create sandbox" in error_events[0].data["message"]


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_flow_mock(self, mock_settings):
        """Test full flow with mocked dependencies"""
        orchestrator = AgentOrchestrator(mock_settings)
        
        # Mock all external calls
        mock_sandbox = Mock(id="test-sandbox-123")
        orchestrator.manager.create_sandbox = Mock(return_value=mock_sandbox)
        orchestrator.manager.delete_sandbox = Mock()
        orchestrator.manager.execute_command = Mock(
            side_effect=[
                "Cloned",  # Clone
                None,      # Git config
                None,      # Git config
                None,      # Git config
                None,      # Create branch
                "Claude output",  # Claude execution
                "M file.py",      # Git status
                None,      # Git add
                None,      # Git commit
                "1 file changed",  # Git diff
                None,      # Git push
                "https://github.com/test/repo/pull/123"  # PR creation
            ]
        )
        
        # Track events
        events = []
        async for event in orchestrator.process_request(
            request_id="test-123",
            repo_url="https://github.com/test/repo",
            prompt="Add a test"
        ):
            events.append(event)
        
        # Verify events
        event_types = [e.type for e in events]
        assert "progress" in event_types
        assert "pr_created" in event_types
        
        # Verify PR was created
        pr_events = [e for e in events if e.type == "pr_created"]
        assert len(pr_events) == 1
        assert pr_events[0].data["pr_url"] == "https://github.com/test/repo/pull/123"


class TestSecurity:
    """Security-related tests"""
    
    def test_api_key_required(self):
        """Test API key authentication when enabled"""
        with patch('config.Settings') as mock_settings:
            mock_settings.return_value.require_auth = True
            mock_settings.return_value.api_key = "test-key"
            
            client = TestClient(app)
            
            # Without API key
            response = client.post(
                "/api/code",
                json={
                    "repo_url": "https://github.com/test/repo",
                    "prompt": "Test"
                }
            )
            assert response.status_code == 401
            
            # With wrong API key
            response = client.post(
                "/api/code",
                json={
                    "repo_url": "https://github.com/test/repo",
                    "prompt": "Test"
                },
                headers={"X-API-Key": "wrong-key"}
            )
            assert response.status_code == 401
    
    def test_input_sanitization(self, test_client):
        """Test input sanitization"""
        # Test SQL injection attempt
        response = test_client.post(
            "/api/code",
            json={
                "repo_url": "https://github.com/test/repo",
                "prompt": "'; DROP TABLE users; --"
            }
        )
        # Should process normally (sanitized in sandbox)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])