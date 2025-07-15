#!/usr/bin/env python3
"""
Comprehensive test suite for Daytona Manager
Tests all functionality with mocked Daytona SDK responses
"""

import pytest
import asyncio
import json
import os
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
from pathlib import Path

from daytona_manager_cleaned import DaytonaManager
from streaming_response import StreamingResponseHandler, StreamChunk, ResponseType
from permission_manager import PermissionManager, OperationType, PermissionLevel


class TestDaytonaManager:
    """Test suite for DaytonaManager class"""
    
    @pytest.fixture
    def mock_daytona(self):
        """Create mock Daytona client"""
        mock = MagicMock()
        mock.list.return_value = []
        return mock
    
    @pytest.fixture
    def manager(self, mock_daytona, monkeypatch):
        """Create DaytonaManager instance with mocked dependencies"""
        monkeypatch.setenv('DAYTONA_API_KEY', 'test-api-key')
        monkeypatch.setenv('DAYTONA_API_URL', 'https://test.daytona.io/api')
        
        with patch('daytona_manager_cleaned.Daytona') as mock_daytona_class:
            mock_daytona_class.return_value = mock_daytona
            manager = DaytonaManager()
            manager.daytona = mock_daytona
            return manager
    
    def test_initialization_success(self, monkeypatch):
        """Test successful initialization with API key"""
        monkeypatch.setenv('DAYTONA_API_KEY', 'test-api-key')
        
        with patch('daytona_manager_cleaned.Daytona') as mock_daytona_class:
            manager = DaytonaManager()
            assert manager.api_key == 'test-api-key'
            mock_daytona_class.assert_called_once()
    
    def test_initialization_no_api_key(self, monkeypatch):
        """Test initialization fails without API key"""
        monkeypatch.delenv('DAYTONA_API_KEY', raising=False)
        
        with pytest.raises(SystemExit):
            DaytonaManager()
    
    def test_create_sandbox_default_name(self, manager, mock_daytona):
        """Test sandbox creation with default name"""
        mock_sandbox = MagicMock()
        mock_sandbox.id = 'sandbox-123'
        mock_daytona.create.return_value = mock_sandbox
        
        result = manager.create_sandbox()
        
        assert result == mock_sandbox
        mock_daytona.create.assert_called_once()
        
        # Check that name contains timestamp
        call_args = mock_daytona.create.call_args[0][0]
        assert 'claude-' in call_args.name
        assert call_args.image == 'node:20-slim'
    
    def test_create_sandbox_custom_type(self, manager, mock_daytona):
        """Test sandbox creation with custom type"""
        mock_sandbox = MagicMock()
        mock_sandbox.id = 'sandbox-456'
        mock_daytona.create.return_value = mock_sandbox
        
        result = manager.create_sandbox(name='test-python', sandbox_type='python')
        
        assert result == mock_sandbox
        call_args = mock_daytona.create.call_args[0][0]
        assert call_args.name == 'test-python'
        assert call_args.image == 'python:3.11-bullseye'
    
    def test_create_sandbox_failure(self, manager, mock_daytona):
        """Test sandbox creation failure handling"""
        mock_daytona.create.side_effect = Exception("API Error")
        
        result = manager.create_sandbox()
        assert result is None
    
    def test_setup_environment_claude(self, manager):
        """Test Claude environment setup"""
        mock_sandbox = MagicMock()
        mock_response = MagicMock()
        mock_response.exit_code = 0
        mock_sandbox.process.exec.return_value = mock_response
        
        manager.setup_environment(mock_sandbox, 'claude')
        
        # Verify Node.js and Claude installation commands
        exec_calls = mock_sandbox.process.exec.call_args_list
        commands = [call[0][0] for call in exec_calls]
        
        assert any('nvm install' in cmd for cmd in commands)
        assert any('claude-code' in cmd for cmd in commands)
    
    def test_setup_claude_auth_with_key(self, manager, monkeypatch):
        """Test Claude authentication setup with API key"""
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-anthropic-key')
        
        mock_sandbox = MagicMock()
        manager.setup_claude_auth(mock_sandbox)
        
        # Verify auth file creation
        exec_calls = mock_sandbox.process.exec.call_args_list
        commands = [call[0][0] for call in exec_calls]
        
        assert any('claude.json' in cmd for cmd in commands)
        assert any('test-anthropic-key' in cmd for cmd in commands)
    
    def test_list_sandboxes_empty(self, manager, mock_daytona):
        """Test listing sandboxes when none exist"""
        mock_daytona.list.return_value = []
        
        manager.list_sandboxes()
        mock_daytona.list.assert_called_once()
    
    def test_list_sandboxes_with_data(self, manager, mock_daytona):
        """Test listing sandboxes with data"""
        mock_sandbox = MagicMock()
        mock_sandbox.id = 'sandbox-789'
        mock_sandbox.name = 'test-sandbox'
        mock_sandbox.status = 'running'
        mock_sandbox.created_at = datetime.now().isoformat()
        
        mock_daytona.list.return_value = [mock_sandbox]
        
        manager.list_sandboxes()
        mock_daytona.list.assert_called_once()
    
    def test_connect_to_sandbox_success(self, manager, mock_daytona):
        """Test successful sandbox connection"""
        mock_sandbox = MagicMock()
        mock_daytona.get.return_value = mock_sandbox
        
        result = manager.connect_to_sandbox('sandbox-123')
        
        assert result == mock_sandbox
        mock_daytona.get.assert_called_once_with('sandbox-123')
    
    def test_connect_to_sandbox_failure(self, manager, mock_daytona):
        """Test sandbox connection failure"""
        mock_daytona.get.side_effect = Exception("Sandbox not found")
        
        result = manager.connect_to_sandbox('invalid-id')
        assert result is None
    
    def test_execute_command_success(self, manager):
        """Test command execution in sandbox"""
        mock_sandbox = MagicMock()
        mock_response = MagicMock()
        mock_response.result = "Hello World\n"
        mock_sandbox.process.exec.return_value = mock_response
        
        result = manager.execute_command(mock_sandbox, "echo 'Hello World'")
        
        assert result == "Hello World"
        mock_sandbox.process.exec.assert_called_once_with("echo 'Hello World'")
    
    def test_delete_sandbox_success(self, manager, mock_daytona):
        """Test sandbox deletion"""
        mock_sandbox = MagicMock()
        mock_daytona.get.return_value = mock_sandbox
        
        manager.delete_sandbox('sandbox-123')
        
        mock_daytona.get.assert_called_once_with('sandbox-123')
        mock_sandbox.delete.assert_called_once()


class TestStreamingResponse:
    """Test suite for StreamingResponseHandler"""
    
    @pytest.fixture
    def handler(self):
        """Create StreamingResponseHandler instance"""
        return StreamingResponseHandler()
    
    @pytest.mark.asyncio
    async def test_stream_claude_response_thinking(self, handler):
        """Test streaming response with thinking events"""
        def mock_exec(cmd):
            return MagicMock(
                result='{"type": "thinking", "content": "Analyzing the problem..."}'
            )
        
        chunks = []
        async for chunk in handler.stream_claude_response("test", mock_exec):
            chunks.append(chunk)
        
        assert len(chunks) >= 2  # Initial thinking + parsed thinking
        assert any(chunk.type == ResponseType.THINKING for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_stream_claude_response_code(self, handler):
        """Test streaming response with code blocks"""
        def mock_exec(cmd):
            return MagicMock(
                result='{"type": "content", "content": "```python\\nprint(\\"test\\")\\n```"}'
            )
        
        chunks = []
        async for chunk in handler.stream_claude_response("test", mock_exec):
            chunks.append(chunk)
        
        code_chunks = [c for c in chunks if c.type == ResponseType.CODE]
        assert len(code_chunks) > 0
        assert code_chunks[0].metadata['language'] == 'python'
    
    @pytest.mark.asyncio
    async def test_stream_claude_response_error(self, handler):
        """Test streaming response error handling"""
        def mock_exec(cmd):
            raise Exception("Connection failed")
        
        chunks = []
        async for chunk in handler.stream_claude_response("test", mock_exec):
            chunks.append(chunk)
        
        error_chunks = [c for c in chunks if c.type == ResponseType.ERROR]
        assert len(error_chunks) > 0
        assert "Connection failed" in error_chunks[0].content
    
    def test_detect_language(self, handler):
        """Test language detection from code blocks"""
        assert handler._detect_language("```python") == "python"
        assert handler._detect_language("```javascript") == "javascript"
        assert handler._detect_language("```bash") == "bash"
        assert handler._detect_language("```unknown") == "text"
    
    @pytest.mark.asyncio
    async def test_show_operation_progress(self, handler):
        """Test progress indicator for operations"""
        steps = [
            {"name": "Step 1", "command": "echo 1"},
            {"name": "Step 2", "command": "echo 2"},
        ]
        
        def mock_exec(cmd):
            return MagicMock(result="Done")
        
        await handler.show_operation_progress("Test Operation", steps, mock_exec)


class TestPermissionManager:
    """Test suite for PermissionManager"""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for test files"""
        return tmp_path
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create PermissionManager instance with temp files"""
        config_file = str(temp_dir / "permissions.json")
        audit_file = str(temp_dir / "audit.log")
        return PermissionManager(config_file=config_file, audit_file=audit_file)
    
    def test_initialization(self, manager, temp_dir):
        """Test permission manager initialization"""
        assert manager.config_file.parent.exists()
        assert manager.saved_permissions == {}
        assert manager.session_permissions == {}
    
    def test_request_permission_first_time(self, manager, monkeypatch):
        """Test permission request for first time"""
        # Mock user input
        monkeypatch.setattr('rich.prompt.Confirm.ask', lambda *args, **kwargs: True)
        
        allowed = manager.request_permission(
            OperationType.CREATE_SANDBOX,
            "test-sandbox",
            {"size": "small"},
            risk_level="low"
        )
        
        assert allowed is True
    
    def test_save_and_load_permissions(self, manager, temp_dir):
        """Test saving and loading permissions"""
        # Save a permission
        manager.saved_permissions["create_sandbox:test"] = {
            'level': PermissionLevel.ALWAYS_ALLOW.value,
            'timestamp': 123456789
        }
        manager._save_permissions()
        
        # Create new manager to test loading
        new_manager = PermissionManager(
            config_file=str(manager.config_file),
            audit_file=str(manager.audit_file)
        )
        
        assert "create_sandbox:test" in new_manager.saved_permissions
    
    def test_session_permissions(self, manager):
        """Test session-only permissions"""
        request = MagicMock()
        request.operation = OperationType.EXECUTE_COMMAND
        request.resource = "temp-command"
        
        key = manager._get_permission_key(request)
        manager.session_permissions[key] = True
        
        result = manager._check_saved_permission(request)
        assert result is True
    
    def test_audit_logging(self, manager):
        """Test audit log functionality"""
        request = MagicMock()
        request.operation = OperationType.DELETE_SANDBOX
        request.resource = "old-sandbox"
        request.details = {"age": "30 days"}
        request.timestamp = 123456789
        request.risk_level = "high"
        
        decision = MagicMock()
        decision.request = request
        decision.allowed = False
        decision.reason = "User denied"
        decision.remember = False
        decision.timestamp = 123456789
        
        manager._log_decision(decision)
        
        # Check audit log
        entries = manager.get_audit_log()
        assert len(entries) > 0
        assert entries[0]['allowed'] is False
    
    def test_reset_permissions(self, manager):
        """Test resetting permissions"""
        # Add some permissions
        manager.saved_permissions["test:1"] = {'level': 'allow', 'timestamp': 123}
        manager.session_permissions["test:2"] = True
        
        # Reset all
        manager.reset_permissions("all")
        
        assert len(manager.saved_permissions) == 0
        assert len(manager.session_permissions) == 0
    
    def test_batch_permissions_context(self, manager, monkeypatch):
        """Test batch permissions context manager"""
        monkeypatch.setattr('rich.prompt.Confirm.ask', lambda *args, **kwargs: True)
        
        from permission_manager import BatchPermissions
        
        with BatchPermissions(manager, OperationType.INSTALL_SOFTWARE) as allowed:
            assert allowed is True


class TestIntegration:
    """Integration tests for all components"""
    
    @pytest.mark.asyncio
    async def test_streaming_with_permissions(self, tmp_path, monkeypatch):
        """Test streaming response with permission checks"""
        # Setup
        monkeypatch.setenv('DAYTONA_API_KEY', 'test-key')
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-anthropic-key')
        
        # Mock user approval
        monkeypatch.setattr('rich.prompt.Confirm.ask', lambda *args, **kwargs: True)
        
        # Create components
        with patch('daytona_manager_cleaned.Daytona'):
            manager = DaytonaManager()
            
        perm_manager = PermissionManager(
            config_file=str(tmp_path / "perms.json"),
            audit_file=str(tmp_path / "audit.log")
        )
        stream_handler = StreamingResponseHandler()
        
        # Test permission request
        allowed = perm_manager.request_permission(
            OperationType.EXECUTE_COMMAND,
            "test-sandbox",
            {"command": "claude --help"}
        )
        
        assert allowed is True
        
        # Test streaming if allowed
        if allowed:
            async def mock_exec(cmd):
                return MagicMock(result='{"type": "content", "content": "Help content"}')
            
            chunks = []
            async for chunk in stream_handler.stream_claude_response("claude --help", mock_exec):
                chunks.append(chunk)
            
            assert len(chunks) > 0


# Test utilities
def test_main_cli_help(capsys, monkeypatch):
    """Test CLI help output"""
    monkeypatch.setenv('DAYTONA_API_KEY', 'test-key')
    
    with patch('sys.argv', ['daytona_manager_cleaned.py']):
        with patch('daytona_manager_cleaned.DaytonaManager'):
            from daytona_manager_cleaned import main
            main()
    
    captured = capsys.readouterr()
    assert "Daytona Development Environment Manager" in captured.out
    assert "create" in captured.out
    assert "list" in captured.out
    assert "connect" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])