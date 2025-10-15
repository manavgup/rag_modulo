# IBM Cloud Monitoring Module
# This module sets up comprehensive monitoring and observability for RAG Modulo

terraform {
  required_version = ">= 1.5"
  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = "~> 1.0"
    }
  }
}

# IBM Cloud Monitoring service
resource "ibm_resource_instance" "monitoring" {
  name              = "${var.project_name}-monitoring"
  service           = "sysdig-monitor"
  plan              = var.monitoring_plan
  location          = var.region
  resource_group_id = var.resource_group_id

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:monitoring",
    "managed:true"
  ]

  lifecycle {
    prevent_destroy = var.environment == "production"
  }
}

# Monitoring service credentials
resource "ibm_resource_key" "monitoring_credentials" {
  name                 = "${var.project_name}-monitoring-credentials"
  role                 = "Manager"
  resource_instance_id = ibm_resource_instance.monitoring.id
}

# Log Analysis service
resource "ibm_resource_instance" "log_analysis" {
  name              = "${var.project_name}-log-analysis"
  service           = "logdna"
  plan              = var.log_analysis_plan
  location          = var.region
  resource_group_id = var.resource_group_id

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:log-analysis",
    "managed:true"
  ]

  lifecycle {
    prevent_destroy = var.environment == "production"
  }
}

# Log Analysis service credentials
resource "ibm_resource_key" "log_analysis_credentials" {
  name                 = "${var.project_name}-log-analysis-credentials"
  role                 = "Manager"
  resource_instance_id = ibm_resource_instance.log_analysis.id
}

# Application Performance Monitoring
resource "ibm_resource_instance" "apm" {
  name              = "${var.project_name}-apm"
  service           = "appid"
  plan              = var.apm_plan
  location          = var.region
  resource_group_id = var.resource_group_id

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:apm",
    "managed:true"
  ]

  lifecycle {
    prevent_destroy = var.environment == "production"
  }
}

# APM service credentials
resource "ibm_resource_key" "apm_credentials" {
  name                 = "${var.project_name}-apm-credentials"
  role                 = "Manager"
  resource_instance_id = ibm_resource_instance.apm.id
}

# Monitoring dashboard configuration
resource "ibm_resource_instance" "dashboard" {
  name              = "${var.project_name}-dashboard"
  service           = "dashdb"
  plan              = var.dashboard_plan
  location          = var.region
  resource_group_id = var.resource_group_id

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:dashboard",
    "managed:true"
  ]

  lifecycle {
    prevent_destroy = var.environment == "production"
  }
}

# Dashboard service credentials
resource "ibm_resource_key" "dashboard_credentials" {
  name                 = "${var.project_name}-dashboard-credentials"
  role                 = "Manager"
  resource_instance_id = ibm_resource_instance.dashboard.id
}

# Alert webhook configuration
resource "ibm_function_action" "alert_webhook" {
  name = "${var.project_name}-alert-webhook"

  exec {
    kind = "nodejs:16"
    code = <<EOF
function main(params) {
  const alert = params.alert;
  const severity = alert.severity || 'warning';
  const message = alert.message || 'No message provided';
  const timestamp = new Date().toISOString();

  // Send alert to webhook URL
  const webhookUrl = params.webhook_url;
  if (webhookUrl) {
    const payload = {
      text: `[${severity.toUpperCase()}] ${message}`,
      timestamp: timestamp,
      source: 'rag-modulo-monitoring'
    };

    // In a real implementation, you would send this to your webhook
    console.log('Alert webhook payload:', JSON.stringify(payload, null, 2));
  }

  return {
    status: 'success',
    message: 'Alert processed',
    timestamp: timestamp
  };
}
EOF
  }

  parameters = {
    webhook_url = var.alert_webhook_url
  }

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:alerting"
  ]
}

# Monitoring triggers
resource "ibm_function_trigger" "high_cpu_trigger" {
  name = "${var.project_name}-high-cpu-trigger"

  feed {
    name = "/whisk.system/alarms/interval"
    parameters = jsonencode({
      trigger_payload = "high-cpu"
      cron = "*/5 * * * *"  # Every 5 minutes
    })
  }

  user_defined_annotations = jsonencode({
    "description" = "Trigger for high CPU usage alerts"
  })

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:alerting"
  ]
}

resource "ibm_function_trigger" "high_memory_trigger" {
  name = "${var.project_name}-high-memory-trigger"

  feed {
    name = "/whisk.system/alarms/interval"
    parameters = jsonencode({
      trigger_payload = "high-memory"
      cron = "*/5 * * * *"  # Every 5 minutes
    })
  }

  user_defined_annotations = jsonencode({
    "description" = "Trigger for high memory usage alerts"
  })

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:alerting"
  ]
}

# Monitoring rules
resource "ibm_function_rule" "high_cpu_rule" {
  name = "${var.project_name}-high-cpu-rule"
  trigger_name = ibm_function_trigger.high_cpu_trigger.name
  action_name = ibm_function_action.alert_webhook.name

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:alerting"
  ]
}

resource "ibm_function_rule" "high_memory_rule" {
  name = "${var.project_name}-high-memory-rule"
  trigger_name = ibm_function_trigger.high_memory_trigger.name
  action_name = ibm_function_action.alert_webhook.name

  tags = [
    "project:${var.project_name}",
    "environment:${var.environment}",
    "service:alerting"
  ]
}
