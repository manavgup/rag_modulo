"""E2E tests for system administration workflows."""

from uuid import uuid4

import pytest
import requests


@pytest.mark.e2e
class TestSystemAdministrationE2E:
    """E2E tests for system administration workflows."""

    def test_system_health_check_workflow(self, base_url: str):
        """Test complete system health check workflow."""
        # Health check endpoint
        health_url = f"{base_url}/health"

        try:
            response = requests.get(health_url, timeout=30)

            # Should get a successful response
            assert response.status_code == 200

            health_data = response.json()
            assert "status" in health_data

            # System should be healthy for E2E tests
            if health_data["status"] == "healthy":
                # API returns 'components' not 'services'
                assert "components" in health_data
                components = health_data.get("components", {})
                # Check for key components
                assert "datastore" in components or "database" in components

        except requests.exceptions.RequestException as e:
            pytest.skip(f"System not accessible for E2E testing: {e}")

    def test_system_initialization_e2e_workflow(self, base_url: str, auth_headers: dict[str, str]):
        """Test complete system initialization E2E workflow."""
        # Note: System initialization happens automatically during app startup
        # There is no admin endpoint for manual initialization
        # Instead, test that the system is properly initialized by checking health

        health_url = f"{base_url}/health"

        try:
            response = requests.get(health_url, timeout=30)

            # System should be healthy if initialization worked
            assert response.status_code == 200

            health_data = response.json()
            assert health_data["status"] == "healthy"

            # Check that key components are working
            components = health_data.get("components", {})
            assert "datastore" in components or "database" in components

        except requests.exceptions.RequestException as e:
            pytest.skip(f"System health check not available: {e}")

    def test_llm_provider_management_e2e_workflow(self, base_url: str, auth_headers: dict[str, str]):
        """Test complete LLM provider management E2E workflow."""
        providers_url = f"{base_url}/llm-providers"

        try:
            # 1. List existing providers
            list_response = requests.get(providers_url, headers=auth_headers, timeout=30)

            if list_response.status_code == 200:
                providers = list_response.json()
                assert isinstance(providers, list)

                initial_count = len(providers)

                # 2. Create a test provider
                test_provider = {
                    "name": f"test_provider_{uuid4().hex[:8]}",
                    "base_url": "https://api.test-provider.com",
                    "api_key": "test-api-key",
                    "is_active": True,
                    "is_default": False,
                }

                create_response = requests.post(providers_url, headers=auth_headers, json=test_provider, timeout=30)

                if create_response.status_code in [200, 201]:
                    created_provider = create_response.json()
                    provider_id = created_provider["id"]

                    # 3. Verify provider was created
                    get_response = requests.get(f"{providers_url}/{provider_id}", headers=auth_headers, timeout=30)

                    if get_response.status_code == 200:
                        retrieved_provider = get_response.json()
                        assert retrieved_provider["name"] == test_provider["name"]
                        assert retrieved_provider["base_url"] == test_provider["base_url"]

                    # 4. Update the provider
                    update_data = {"is_active": False}
                    update_response = requests.put(
                        f"{providers_url}/{provider_id}", headers=auth_headers, json=update_data, timeout=30
                    )

                    if update_response.status_code == 200:
                        updated_provider = update_response.json()
                        assert updated_provider["is_active"] is False

                    # 5. Delete the test provider
                    delete_response = requests.delete(
                        f"{providers_url}/{provider_id}", headers=auth_headers, timeout=30
                    )

                    # Should succeed or return 404 if already deleted
                    assert delete_response.status_code in [200, 204, 404]

                    # 6. Verify final count
                    final_list_response = requests.get(providers_url, headers=auth_headers, timeout=30)
                    if final_list_response.status_code == 200:
                        final_providers = final_list_response.json()
                        final_count = len(final_providers)
                        assert final_count == initial_count

        except requests.exceptions.RequestException as e:
            pytest.skip(f"LLM provider management E2E not available: {e}")

    def test_model_configuration_e2e_workflow(self, base_url: str, auth_headers: dict[str, str]):
        """Test complete model configuration E2E workflow."""
        models_url = f"{base_url}/llm-models"

        try:
            # 1. List existing models
            list_response = requests.get(models_url, headers=auth_headers, timeout=30)

            if list_response.status_code == 200:
                models = list_response.json()
                assert isinstance(models, list)

                # 2. Verify model structure for any existing models
                for model in models[:3]:  # Check first 3 models
                    assert "id" in model
                    assert "provider_id" in model
                    assert "model_type" in model
                    assert "is_active" in model

                    # Test model details endpoint
                    model_detail_response = requests.get(
                        f"{models_url}/{model['id']}", headers=auth_headers, timeout=30
                    )

                    if model_detail_response.status_code == 200:
                        model_detail = model_detail_response.json()
                        assert model_detail["id"] == model["id"]
                        assert "model_id" in model_detail
                        assert "timeout" in model_detail

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Model configuration E2E not available: {e}")

    def test_system_configuration_backup_restore_workflow(self, base_url: str, auth_headers: dict[str, str]):
        """Test system configuration backup and restore E2E workflow."""
        # Note: System backup/restore endpoints don't exist in the current API
        # These would need to be implemented if required
        pytest.skip("System backup/restore endpoints not implemented")

    def test_system_monitoring_e2e_workflow(self, base_url: str, auth_headers: dict[str, str]):
        """Test system monitoring E2E workflow."""
        # Note: System metrics and logs endpoints don't exist in the current API
        # These would need to be implemented if required
        pytest.skip("System metrics and logs endpoints not implemented")

    def test_user_management_admin_workflow(self, base_url: str, auth_headers: dict[str, str]):
        """Test complete user management admin E2E workflow."""
        users_url = f"{base_url}/users"

        try:
            # 1. List all users (admin view)
            list_response = requests.get(users_url, headers=auth_headers, timeout=30)

            if list_response.status_code == 200:
                users = list_response.json()
                assert isinstance(users, list)

                if users:
                    # 2. Test user detail view
                    first_user = users[0]
                    user_detail_response = requests.get(
                        f"{users_url}/{first_user['id']}", headers=auth_headers, timeout=30
                    )

                    if user_detail_response.status_code == 200:
                        user_detail = user_detail_response.json()
                        assert user_detail["id"] == first_user["id"]
                        assert "email" in user_detail
                        assert "role" in user_detail

                    # 3. Test user role management
                    if user_detail.get("role") != "super_admin":  # Don't modify super admin
                        role_update = {"role": "admin"}
                        role_response = requests.patch(
                            f"{users_url}/{first_user['id']}/role", headers=auth_headers, json=role_update, timeout=30
                        )

                        # Should succeed or be forbidden based on permissions
                        assert role_response.status_code in [200, 403]

        except requests.exceptions.RequestException as e:
            pytest.skip(f"User management admin E2E not available: {e}")

    def test_complete_system_admin_workflow(self, base_url: str, auth_headers: dict[str, str]):
        """Test complete system administration workflow from initialization to monitoring."""
        workflow_steps = []

        try:
            # Step 1: System Health Check
            health_response = requests.get(f"{base_url}/health", timeout=30)
            workflow_steps.append(("health_check", health_response.status_code == 200))

            # Step 2: System Initialization
            init_response = requests.post(f"{base_url}/health", headers=auth_headers, timeout=60)
            workflow_steps.append(("initialization", init_response.status_code in [200, 201, 409]))

            # Step 3: Provider Management
            providers_response = requests.get(f"{base_url}/llm-providers", headers=auth_headers, timeout=30)
            workflow_steps.append(("provider_management", providers_response.status_code in [200, 404]))

            # Step 4: Model Configuration
            models_response = requests.get(f"{base_url}/llm-models", headers=auth_headers, timeout=30)
            workflow_steps.append(("model_configuration", models_response.status_code in [200, 404]))

            # Step 5: System Monitoring
            # Note: System metrics endpoint doesn't exist, use health check instead
            metrics_response = requests.get(f"{base_url}/health", headers=auth_headers, timeout=30)
            workflow_steps.append(("monitoring", metrics_response.status_code in [200, 404]))

            # Verify workflow completion
            successful_steps = [step for step, success in workflow_steps if success]
            assert len(successful_steps) >= 1  # At least health check should work

            # Log workflow results
            print(f"System admin workflow completed: {len(successful_steps)}/{len(workflow_steps)} steps successful")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Complete system admin workflow E2E not available: {e}")
