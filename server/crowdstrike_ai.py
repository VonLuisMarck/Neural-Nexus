import json
import time
import logging
import requests
from typing import Optional
from datetime import datetime, timedelta

class CrowdStrikeAIClient:
    """Direct REST API client for CrowdStrike workflows"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize client from configuration"""
        self.config = self._load_config(config_path)
        
        # Configure CrowdStrike settings
        cs_config = self.config.get('crowdstrike', {})
        self.client_id = cs_config.get('client_id')
        self.client_secret = cs_config.get('client_secret')
        self.base_url = cs_config.get('base_url', 'https://api.crowdstrike.com')
        
        # Execution configuration
        exec_config = self.config.get('execution', {})
        self.default_timeout = exec_config.get('default_timeout', 300)
        self.default_poll_interval = exec_config.get('default_poll_interval', 10)  # Aumentado a 10 segundos
        
        # Authentication
        self.access_token = None
        self.token_expires_at = None
        
        # Simple logging setup
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Test authentication on initialization
        self._authenticate()
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Error loading config: {e}")
    
    def _authenticate(self):
        """Authenticate with CrowdStrike and get access token"""
        try:
            auth_url = f"{self.base_url}/oauth2/token"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }
            
            self.logger.info("Authenticating with CrowdStrike...")
            response = requests.post(auth_url, headers=headers, data=data)
            
            if response.status_code == 201:
                token_data = response.json()
                self.access_token = token_data['access_token']
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # 1 min buffer
                
                self.logger.info("✅ CrowdStrike authentication successful")
                return True
            else:
                error_msg = f"Authentication failed (Status: {response.status_code}): {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            raise Exception(f"CrowdStrike authentication failed: {str(e)}")
    
    def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        if not self.access_token or datetime.now() >= self.token_expires_at:
            self.logger.info("Token expired or missing, re-authenticating...")
            self._authenticate()
    
    def _extract_output(self, result_data: dict) -> str:
        """Extract workflow output from response data"""
        try:
            # Log the full response for debugging
            self.logger.info(f"Extracting output from: {json.dumps(result_data, indent=2)}")
            
            resources = result_data.get('resources', [])
            if not resources:
                return "ERROR: No resources found in response"
            
            # Get the first resource (execution result)
            resource = resources[0]
            
            # Check activities for results
            activities = resource.get('activities', [])
            if activities:
                for activity in activities:
                    result = activity.get('result', {})
                    
                    # Look for completion field (main AI output)
                    if 'completion' in result and result['completion']:
                        return str(result['completion'])
                    
                    # Look for other common AI output fields
                    for field in ['output', 'response', 'text', 'content', 'answer', 'message']:
                        if field in result and result[field]:
                            return str(result[field])
            
            # Check trigger result
            trigger = resource.get('trigger', {})
            if trigger and 'result' in trigger:
                trigger_result = trigger['result']
                for field in ['completion', 'output', 'response', 'text', 'content', 'answer', 'message']:
                    if field in trigger_result and trigger_result[field]:
                        return str(trigger_result[field])
            
            # Check output_data
            output_data = resource.get('output_data', {})
            if output_data:
                for field in ['completion', 'output', 'response', 'text', 'content', 'answer', 'message']:
                    if field in output_data and output_data[field]:
                        return str(output_data[field])
            
            # Fallback: return summary or entire resource
            summary = resource.get('summary', '')
            if summary:
                return summary
            
            return json.dumps(resource, indent=2)
            
        except Exception as e:
            return f"ERROR: Failed to extract output - {str(e)}"
    
    def run_workflow(
        self, 
        workflow_id: str, 
        prompt: str, 
        timeout: Optional[int] = None
    ) -> str:
        """
        Execute a workflow and return output as string
        
        Args:
            workflow_id: CrowdStrike workflow ID
            prompt: Input prompt for the workflow
            timeout: Maximum wait time in seconds
            
        Returns:
            String with workflow output
        """
        
        if timeout is None:
            timeout = self.default_timeout
        
        start_time = time.time()
        
        try:
            # Execute workflow using correct API format
            self._ensure_authenticated()
            
            url = f"{self.base_url}/workflows/entities/execute/v1"
            
            # Headers
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Query parameters (definition_id goes here)
            params = {
                'definition_id': workflow_id
            }
            
            # Body (the prompt as JSON object)
            body_data = {
                "prompt": prompt,
                "input": prompt
            }
            
            self.logger.info(f"Executing workflow {workflow_id}")
            self.logger.info(f"URL: {url}")
            self.logger.info(f"Params: {params}")
            self.logger.info(f"Body: {body_data}")
            
            response = requests.post(url, headers=headers, params=params, json=body_data, timeout=30)
            
            self.logger.info(f"Response status: {response.status_code}")
            self.logger.info(f"Response: {response.text}")
            
            # Check response
            if response.status_code not in [200, 201]:
                try:
                    error_data = response.json()
                    errors = error_data.get('errors', [])
                    error_msg = errors[0].get('message', 'Unknown error') if errors else 'Execution failed'
                except:
                    error_msg = response.text
                
                return f"ERROR: Workflow execution failed - {error_msg} (Status: {response.status_code})\nFull response: {json.dumps(response.json() if response.content else {}, indent=2)}"
            
            # Extract execution_id from response
            response_data = response.json()
            resources = response_data.get('resources', [])
            
            if not resources:
                return f"ERROR: No execution ID returned. Response: {json.dumps(response_data, indent=2)}"
            
            execution_id = resources[0]
            self.logger.info(f"Workflow execution started with ID: {execution_id}")
            
        except Exception as e:
            return f"ERROR: Failed to execute workflow - {str(e)}"
        
        # Wait initial time before first poll (let the workflow start)
        self.logger.info(f"Waiting 15 seconds before first poll...")
        time.sleep(15)
        
        # Wait for completion
        poll_count = 0
        max_polls = timeout // self.default_poll_interval
        
        while time.time() - start_time < timeout:
            poll_count += 1
            
            try:
                # Get execution results using correct API format
                self._ensure_authenticated()
                
                results_url = f"{self.base_url}/workflows/entities/execution-results/v1"
                
                headers = {
                    'Authorization': f'Bearer {self.access_token}',
                    'Accept': 'application/json'
                }
                
                # Query parameters (ids goes here)
                params = {
                    'ids': execution_id
                }
                
                self.logger.info(f"Poll {poll_count}/{max_polls}: Checking results for execution {execution_id}")
                
                result_response = requests.get(results_url, headers=headers, params=params, timeout=30)
                
                self.logger.info(f"Poll {poll_count} - Status: {result_response.status_code}")
                self.logger.info(f"Poll {poll_count} - Response: {result_response.text}")
                
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    resources = result_data.get('resources', [])
                    
                    if resources:
                        resource = resources[0]
                        status = resource.get('status', 'unknown')
                        self.logger.info(f"Poll {poll_count} - Workflow status: {status}")
                        
                        # Check for completion
                        if status.lower() in ['completed', 'success', 'finished']:
                            output = self._extract_output(result_data)
                            self.logger.info(f"Workflow completed successfully after {poll_count} polls")
                            return output
                        elif status.lower() in ['failed', 'error', 'cancelled']:
                            error_details = resource.get('error_message', resource.get('summary', 'Unknown error'))
                            return f"ERROR: Workflow failed with status '{status}' - {error_details}"
                        elif status.lower() in ['running', 'in progress', 'pending']:
                            self.logger.info(f"Poll {poll_count} - Workflow still {status}, continuing to wait...")
                        else:
                            self.logger.info(f"Poll {poll_count} - Unknown status '{status}', continuing to wait...")
                    else:
                        self.logger.warning(f"Poll {poll_count} - No resources in response yet")
                else:
                    self.logger.warning(f"Poll {poll_count} - Non-200 response: {result_response.status_code}")
                
            except Exception as e:
                self.logger.warning(f"Poll {poll_count} - Error polling results: {e}")
                pass
            
            # Wait before next poll
            self.logger.info(f"Waiting {self.default_poll_interval} seconds before next poll...")
            time.sleep(self.default_poll_interval)
        
        return f"ERROR: Workflow timed out after {timeout} seconds ({poll_count} polls)"

# Global function for direct use
def execute_crowdstrike_workflow(workflow_id: str, prompt: str, config_path: str = "config.json") -> str:
    """
    Global function to execute a CrowdStrike workflow
    
    Args:
        workflow_id: Workflow ID
        prompt: Input prompt
        config_path: Path to configuration file
        
    Returns:
        String with workflow output
    """
    client = CrowdStrikeAIClient(config_path)
    return client.run_workflow(workflow_id, prompt)
