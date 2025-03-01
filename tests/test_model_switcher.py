"""
Tests for the ModelSwitcher class.
"""
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from ha_agent.models import ModelSwitcher


class TestModelSwitcher(unittest.TestCase):
    """Test cases for the ModelSwitcher class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.local_model = MagicMock()
        self.cloud_model = MagicMock()
        self.switcher = ModelSwitcher(
            local_model=self.local_model,
            cloud_model=self.cloud_model,
            default_to_local=True
        )
    
    def test_init_with_default_to_local(self):
        """Test initialization with default_to_local=True."""
        self.assertEqual(self.switcher.current_model, self.local_model)
        self.assertTrue(self.switcher.default_to_local)
    
    def test_init_with_default_to_cloud(self):
        """Test initialization with default_to_local=False."""
        switcher = ModelSwitcher(
            local_model=self.local_model,
            cloud_model=self.cloud_model,
            default_to_local=False
        )
        self.assertEqual(switcher.current_model, self.cloud_model)
        self.assertFalse(switcher.default_to_local)
    
    def test_force_local(self):
        """Test forcing local model selection."""
        # First set to cloud model
        self.switcher.current_model = self.cloud_model
        
        # Force local
        result = self.switcher.force_local()
        
        # Should return and set to local model
        self.assertEqual(result, self.local_model)
        self.assertEqual(self.switcher.current_model, self.local_model)
    
    def test_force_cloud(self):
        """Test forcing cloud model selection."""
        # Force cloud
        result = self.switcher.force_cloud()
        
        # Should return and set to cloud model
        self.assertEqual(result, self.cloud_model)
        self.assertEqual(self.switcher.current_model, self.cloud_model)
    
    def test_select_model_force_local(self):
        """Test select_model with force_model='local'."""
        result = self.switcher.select_model(force_model="local")
        self.assertEqual(result, self.local_model)
        self.assertEqual(self.switcher.current_model, self.local_model)
    
    def test_select_model_force_cloud(self):
        """Test select_model with force_model='cloud'."""
        result = self.switcher.select_model(force_model="cloud")
        self.assertEqual(result, self.cloud_model)
        self.assertEqual(self.switcher.current_model, self.cloud_model)
    
    def test_select_model_high_complexity(self):
        """Test select_model with high complexity and no latency sensitivity."""
        result = self.switcher.select_model(task_complexity=8, latency_sensitive=False)
        self.assertEqual(result, self.cloud_model)
        self.assertEqual(self.switcher.current_model, self.cloud_model)
    
    def test_select_model_latency_sensitive(self):
        """Test select_model with latency sensitivity."""
        # Set to cloud model first
        self.switcher.current_model = self.cloud_model
        
        # Should select local model due to latency sensitivity
        result = self.switcher.select_model(task_complexity=8, latency_sensitive=True)
        self.assertEqual(result, self.local_model)
        self.assertEqual(self.switcher.current_model, self.local_model)
    
    def test_select_model_low_complexity(self):
        """Test select_model with low complexity."""
        # Set to cloud model first
        self.switcher.current_model = self.cloud_model
        
        # Should select local model due to low complexity
        result = self.switcher.select_model(task_complexity=3, latency_sensitive=False)
        self.assertEqual(result, self.local_model)
        self.assertEqual(self.switcher.current_model, self.local_model)
    
    def test_select_model_medium_complexity(self):
        """Test select_model with medium complexity and no latency sensitivity."""
        # Should default to local model for medium complexity
        result = self.switcher.select_model(task_complexity=6, latency_sensitive=False)
        self.assertEqual(result, self.local_model)
        self.assertEqual(self.switcher.current_model, self.local_model)
        
        # Create a switcher with default_to_local=False
        switcher = ModelSwitcher(
            local_model=self.local_model,
            cloud_model=self.cloud_model,
            default_to_local=False
        )
        
        # Should default to cloud model for medium complexity
        result = switcher.select_model(task_complexity=6, latency_sensitive=False)
        self.assertEqual(result, self.cloud_model)
        self.assertEqual(switcher.current_model, self.cloud_model)
    
    def test_get_model_type(self):
        """Test get_model_type method."""
        self.switcher.current_model = self.local_model
        self.assertEqual(self.switcher.get_model_type(), "local")
        
        self.switcher.current_model = self.cloud_model
        self.assertEqual(self.switcher.get_model_type(), "cloud")
    
    def test_invalid_task_complexity(self):
        """Test handling of invalid task complexity values."""
        # Too low
        result = self.switcher.select_model(task_complexity=-1)
        self.assertEqual(result, self.local_model)  # Should default to local for medium complexity
        
        # Too high
        result = self.switcher.select_model(task_complexity=11)
        self.assertEqual(result, self.local_model)  # Should default to local for medium complexity


if __name__ == "__main__":
    unittest.main() 