-- Migration: Add agents table for SPIFFE/SPIRE workload identity
-- Reference: docs/architecture/spire-integration-architecture.md
--
-- This migration creates the agents table to store AI agent identities
-- with SPIFFE-based authentication support.

-- Create agents table
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spiffe_id VARCHAR(512) UNIQUE NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE
);

-- Add comments
COMMENT ON TABLE agents IS 'AI agents with SPIFFE-based workload identity for RAG Modulo';
COMMENT ON COLUMN agents.spiffe_id IS 'Full SPIFFE ID (e.g., spiffe://rag-modulo.example.com/agent/search-enricher/abc123)';
COMMENT ON COLUMN agents.agent_type IS 'Type of agent (search-enricher, cot-reasoning, etc.)';
COMMENT ON COLUMN agents.capabilities IS 'JSON array of granted capabilities (search:read, llm:invoke, etc.)';
COMMENT ON COLUMN agents.metadata IS 'Additional agent metadata as JSON';
COMMENT ON COLUMN agents.status IS 'Agent status: active, suspended, revoked, pending';
COMMENT ON COLUMN agents.last_seen_at IS 'Last successful authentication timestamp';

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_agents_spiffe_id ON agents(spiffe_id);
CREATE INDEX IF NOT EXISTS idx_agents_agent_type ON agents(agent_type);
CREATE INDEX IF NOT EXISTS idx_agents_owner_user_id ON agents(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_agents_team_id ON agents(team_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_created_at ON agents(created_at DESC);

-- Composite indexes for common query patterns (owner+status, type+status, team+status)
CREATE INDEX IF NOT EXISTS ix_agents_owner_status ON agents(owner_user_id, status);
CREATE INDEX IF NOT EXISTS ix_agents_type_status ON agents(agent_type, status);
CREATE INDEX IF NOT EXISTS ix_agents_team_status ON agents(team_id, status);

-- Create GIN index for capabilities JSONB for efficient containment queries
CREATE INDEX IF NOT EXISTS idx_agents_capabilities ON agents USING GIN (capabilities);

-- Add trigger to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_agents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_agents_updated_at ON agents;
CREATE TRIGGER trigger_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_agents_updated_at();
