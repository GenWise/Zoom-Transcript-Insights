import unittest
import os
from unittest.mock import patch

import config

class TestConfig(unittest.TestCase):
    """Tests for the config module."""
    
    @patch.dict(os.environ, {
        "ZOOM_CLIENT_ID": "test_client_id",
        "ZOOM_CLIENT_SECRET": "test_client_secret",
        "ZOOM_ACCOUNT_ID": "test_account_id",
        "ZOOM_WEBHOOK_SECRET": "test_webhook_secret",
        "GOOGLE_CREDENTIALS_FILE": "test_credentials.json",
        "GOOGLE_DRIVE_ROOT_FOLDER": "test_folder_id",
        "CLAUDE_API_KEY": "test_claude_api_key",
        "APP_HOST": "127.0.0.1",
        "APP_PORT": "9000",
        "DEBUG": "True"
    })
    def test_config_loads_from_env(self):
        """Test that config loads values from environment variables."""
        # Reload config to pick up the mocked environment variables
        import importlib
        importlib.reload(config)
        
        # Check Zoom config
        self.assertEqual(config.ZOOM_CLIENT_ID, "test_client_id")
        self.assertEqual(config.ZOOM_CLIENT_SECRET, "test_client_secret")
        self.assertEqual(config.ZOOM_ACCOUNT_ID, "test_account_id")
        self.assertEqual(config.ZOOM_WEBHOOK_SECRET, "test_webhook_secret")
        
        # Check Google Drive config
        self.assertEqual(config.GOOGLE_CREDENTIALS_FILE, "test_credentials.json")
        self.assertEqual(config.GOOGLE_DRIVE_ROOT_FOLDER, "test_folder_id")
        
        # Check Claude API config
        self.assertEqual(config.CLAUDE_API_KEY, "test_claude_api_key")
        self.assertEqual(config.CLAUDE_MODEL, "claude-3-7-sonnet-20250219")
        
        # Check FastAPI settings
        self.assertEqual(config.APP_HOST, "127.0.0.1")
        self.assertEqual(config.APP_PORT, 9000)
        self.assertTrue(config.DEBUG)
    
    def test_folder_structure(self):
        """Test that folder structure templates are defined correctly."""
        self.assertIn("course_folder", config.FOLDER_STRUCTURE)
        self.assertIn("session_folder", config.FOLDER_STRUCTURE)
        self.assertIn("files", config.FOLDER_STRUCTURE)
        
        # Check file templates
        files = config.FOLDER_STRUCTURE["files"]
        self.assertIn("transcript", files)
        self.assertIn("chat_log", files)
        self.assertIn("analysis", files)
        self.assertIn("executive_summary", files)
        self.assertIn("pedagogical_analysis", files)
        self.assertIn("aha_moments", files)
        self.assertIn("engagement_metrics", files)
    
    def test_claude_prompts(self):
        """Test that Claude prompts are defined correctly."""
        self.assertIn("executive_summary", config.CLAUDE_PROMPTS)
        self.assertIn("pedagogical_analysis", config.CLAUDE_PROMPTS)
        self.assertIn("aha_moments", config.CLAUDE_PROMPTS)
        self.assertIn("engagement_analysis", config.CLAUDE_PROMPTS)
        
        # Check that prompts contain placeholders
        self.assertIn("{transcript}", config.CLAUDE_PROMPTS["executive_summary"])
        self.assertIn("{transcript}", config.CLAUDE_PROMPTS["pedagogical_analysis"])
        self.assertIn("{transcript}", config.CLAUDE_PROMPTS["aha_moments"])
        self.assertIn("{transcript}", config.CLAUDE_PROMPTS["engagement_analysis"])
        self.assertIn("{school_mapping}", config.CLAUDE_PROMPTS["engagement_analysis"])

if __name__ == "__main__":
    unittest.main() 