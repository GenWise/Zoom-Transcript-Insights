import unittest
from unittest.mock import patch, MagicMock

import main
from app.api.routes import router as api_router
from app.api.webhook import router as webhook_router

class TestMain(unittest.TestCase):
    """Tests for the main application."""
    
    def test_app_structure(self):
        """Test that the app has the expected structure."""
        # Check that the app exists
        self.assertTrue(hasattr(main, "app"), "App not found in main.py")
        
        # Check that the app has routes
        self.assertTrue(hasattr(main.app, "routes"), "App has no routes")
        self.assertTrue(len(main.app.routes) > 0, "App has no routes")
        
        # Check that the API router is included
        api_routes = [route for route in main.app.routes if str(route.path).startswith("/api")]
        self.assertTrue(len(api_routes) > 0, "API routes not found")
        
        # Check that the webhook router is included
        webhook_routes = [route for route in main.app.routes if str(route.path).startswith("/webhook")]
        self.assertTrue(len(webhook_routes) > 0, "Webhook routes not found")
    
    def test_app_configuration(self):
        """Test that the app is configured correctly."""
        # Check that the app has a title
        self.assertTrue(hasattr(main.app, "title"), "App has no title")
        self.assertEqual(main.app.title, "Zoom Transcript Insights", "App has incorrect title")
        
        # Check that the app has a description
        self.assertTrue(hasattr(main.app, "description"), "App has no description")
        self.assertIn("Zoom", main.app.description, "App description does not mention Zoom")
        
        # Check that the app has a version
        self.assertTrue(hasattr(main.app, "version"), "App has no version")
    
    @patch("uvicorn.run")
    def test_main_function(self, mock_run):
        """Test the main function that runs the app."""
        # Mock the main function to avoid actually running the server
        with patch.object(main, "__name__", "__main__"):
            # If there's a main function, call it
            if hasattr(main, "main"):
                main.main()
                
                # Check that uvicorn.run was called
                mock_run.assert_called_once()
            else:
                # If there's no main function, the code is likely in the __main__ block
                # We can't directly test it, but we can check if uvicorn is imported
                self.assertTrue("uvicorn" in dir(main), "uvicorn not imported in main.py")

if __name__ == "__main__":
    unittest.main() 