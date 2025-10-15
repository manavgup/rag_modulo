package tests

import (
	"testing"
	"os"
	"path/filepath"
	"strings"

	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/stretchr/testify/assert"
)

func TestTerraformManagedServicesModule(t *testing.T) {
	t.Parallel()

	// Generate a random name to avoid conflicts
	randomName := strings.ToLower(random.UniqueId())
	
	// Set up Terraform options
	terraformOptions := &terraform.Options{
		TerraformDir: "../modules/ibm-cloud/managed-services",
		Vars: map[string]interface{}{
			"project_name": "test-" + randomName,
			"environment":  "dev",
			"region":       "us-south",
			"resource_group_id": "test-resource-group",
			"postgresql_admin_password": "test-password-123",
		},
		EnvVars: map[string]string{
			"TF_VAR_ibmcloud_api_key": os.Getenv("IBMCLOUD_API_KEY"),
		},
	}

	// Clean up after test
	defer terraform.Destroy(t, terraformOptions)

	// Initialize and apply
	terraform.InitAndApply(t, terraformOptions)

	// Test outputs
	postgresqlHost := terraform.Output(t, terraformOptions, "postgresql_host")
	assert.NotEmpty(t, postgresqlHost, "PostgreSQL host should not be empty")

	objectStorageEndpoint := terraform.Output(t, terraformOptions, "object_storage_endpoint")
	assert.NotEmpty(t, objectStorageEndpoint, "Object Storage endpoint should not be empty")

	zillizEndpoint := terraform.Output(t, terraformOptions, "zilliz_endpoint")
	assert.NotEmpty(t, zillizEndpoint, "Zilliz endpoint should not be empty")

	eventStreamsEndpoint := terraform.Output(t, terraformOptions, "event_streams_endpoint")
	assert.NotEmpty(t, eventStreamsEndpoint, "Event Streams endpoint should not be empty")
}

func TestTerraformCodeEngineModule(t *testing.T) {
	t.Parallel()

	// Generate a random name to avoid conflicts
	randomName := strings.ToLower(random.UniqueId())
	
	// Set up Terraform options
	terraformOptions := &terraform.Options{
		TerraformDir: "../modules/ibm-cloud/code-engine",
		Vars: map[string]interface{}{
			"project_name": "test-" + randomName,
			"environment":  "dev",
			"resource_group_id": "test-resource-group",
			"container_registry_url": "us.icr.io",
			"container_registry_username": "iamapikey",
			"container_registry_password": "test-password",
			"backend_image_tag": "v1.0.0",
			"frontend_image_tag": "v1.0.0",
			"postgresql_host": "test-postgres.example.com",
			"postgresql_port": 5432,
			"postgresql_database": "test_db",
			"postgresql_username": "test_user",
			"postgresql_password": "test_password",
			"postgresql_instance_id": "test-postgres-instance",
			"object_storage_endpoint": "test-storage.example.com",
			"object_storage_access_key": "test_access_key",
			"object_storage_secret_key": "test_secret_key",
			"object_storage_bucket_name": "test-bucket",
			"object_storage_instance_id": "test-storage-instance",
			"zilliz_endpoint": "test-zilliz.example.com",
			"zilliz_api_key": "test_zilliz_key",
			"zilliz_instance_id": "test-zilliz-instance",
			"event_streams_endpoint": "test-kafka.example.com",
			"event_streams_api_key": "test_kafka_key",
			"event_streams_instance_id": "test-kafka-instance",
		},
		EnvVars: map[string]string{
			"TF_VAR_ibmcloud_api_key": os.Getenv("IBMCLOUD_API_KEY"),
		},
	}

	// Clean up after test
	defer terraform.Destroy(t, terraformOptions)

	// Initialize and apply
	terraform.InitAndApply(t, terraformOptions)

	// Test outputs
	projectId := terraform.Output(t, terraformOptions, "project_id")
	assert.NotEmpty(t, projectId, "Project ID should not be empty")

	backendEndpoint := terraform.Output(t, terraformOptions, "backend_endpoint")
	assert.NotEmpty(t, backendEndpoint, "Backend endpoint should not be empty")

	frontendEndpoint := terraform.Output(t, terraformOptions, "frontend_endpoint")
	assert.NotEmpty(t, frontendEndpoint, "Frontend endpoint should not be empty")

	backendHealthEndpoint := terraform.Output(t, terraformOptions, "backend_health_endpoint")
	assert.Contains(t, backendHealthEndpoint, "/health", "Backend health endpoint should contain /health")
}

func TestTerraformEnvironmentConfiguration(t *testing.T) {
	t.Parallel()

	// Test development environment
	t.Run("DevelopmentEnvironment", func(t *testing.T) {
		terraformOptions := &terraform.Options{
			TerraformDir: "../environments/ibm",
			Vars: map[string]interface{}{
				"project_name": "test-dev",
				"environment":  "dev",
				"region":       "us-south",
				"resource_group_name": "test-resource-group",
				"ibmcloud_api_key": "test-api-key",
				"container_registry_username": "iamapikey",
				"container_registry_password": "test-password",
				"postgresql_admin_password": "test-password-123",
			},
		}

		// Clean up after test
		defer terraform.Destroy(t, terraformOptions)

		// Initialize and apply
		terraform.InitAndApply(t, terraformOptions)

		// Test outputs
		projectName := terraform.Output(t, terraformOptions, "project_name")
		assert.Equal(t, "test-dev", projectName, "Project name should match")

		environment := terraform.Output(t, terraformOptions, "environment")
		assert.Equal(t, "dev", environment, "Environment should be dev")
	})

	// Test production environment
	t.Run("ProductionEnvironment", func(t *testing.T) {
		terraformOptions := &terraform.Options{
			TerraformDir: "../environments/ibm",
			Vars: map[string]interface{}{
				"project_name": "test-prod",
				"environment":  "production",
				"region":       "us-south",
				"resource_group_name": "test-resource-group",
				"ibmcloud_api_key": "test-api-key",
				"container_registry_username": "iamapikey",
				"container_registry_password": "test-password",
				"postgresql_admin_password": "test-password-123",
				"enable_production_safeguards": true,
			},
		}

		// Clean up after test
		defer terraform.Destroy(t, terraformOptions)

		// Initialize and apply
		terraform.InitAndApply(t, terraformOptions)

		// Test outputs
		projectName := terraform.Output(t, terraformOptions, "project_name")
		assert.Equal(t, "test-prod", projectName, "Project name should match")

		environment := terraform.Output(t, terraformOptions, "environment")
		assert.Equal(t, "production", environment, "Environment should be production")
	})
}

func TestTerraformValidation(t *testing.T) {
	t.Parallel()

	// Test Terraform validation for all modules
	modules := []string{
		"../modules/ibm-cloud/managed-services",
		"../modules/ibm-cloud/code-engine",
		"../modules/ibm-cloud/monitoring",
		"../modules/ibm-cloud/backup",
		"../environments/ibm",
	}

	for _, module := range modules {
		t.Run("Validate_"+filepath.Base(module), func(t *testing.T) {
			terraformOptions := &terraform.Options{
				TerraformDir: module,
			}

			// Run terraform validate
			terraform.Validate(t, terraformOptions)
		})
	}
}

func TestTerraformFormat(t *testing.T) {
	t.Parallel()

	// Test Terraform formatting for all modules
	modules := []string{
		"../modules/ibm-cloud/managed-services",
		"../modules/ibm-cloud/code-engine",
		"../modules/ibm-cloud/monitoring",
		"../modules/ibm-cloud/backup",
		"../environments/ibm",
	}

	for _, module := range modules {
		t.Run("Format_"+filepath.Base(module), func(t *testing.T) {
			terraformOptions := &terraform.Options{
				TerraformDir: module,
			}

			// Run terraform fmt
			terraform.Fmt(t, terraformOptions)
		})
	}
}

func TestTerraformPlan(t *testing.T) {
	t.Parallel()

	// Test Terraform plan for all modules
	modules := []string{
		"../modules/ibm-cloud/managed-services",
		"../modules/ibm-cloud/code-engine",
		"../modules/ibm-cloud/monitoring",
		"../modules/ibm-cloud/backup",
		"../environments/ibm",
	}

	for _, module := range modules {
		t.Run("Plan_"+filepath.Base(module), func(t *testing.T) {
			terraformOptions := &terraform.Options{
				TerraformDir: module,
				Vars: map[string]interface{}{
					"project_name": "test-plan",
					"environment":  "dev",
					"region":       "us-south",
					"resource_group_id": "test-resource-group",
					"ibmcloud_api_key": "test-api-key",
					"container_registry_username": "iamapikey",
					"container_registry_password": "test-password",
					"postgresql_admin_password": "test-password-123",
				},
			}

			// Run terraform plan
			terraform.Plan(t, terraformOptions)
		})
	}
}
