import React, { useEffect, useState } from "react";
import apiClient from "../../services/apiClient";
import { Agent } from "../../services/apiClient";

interface AgentListProps {
  collectionId: string;
}

const AgentList: React.FC<AgentListProps> = ({ collectionId }) => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        setLoading(true);
        const agentList = await apiClient.getAgents();
        setAgents(agentList);
        setError(null);
      } catch (err) {
        setError("Failed to fetch agents.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchAgents();
  }, [collectionId]);

  if (loading) {
    return <div>Loading agents...</div>;
  }

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  return (
    <div>
      {agents.length === 0 ? (
        <p>No agents available for this collection.</p>
      ) : (
        <ul>
          {agents.map((agent) => (
            <li key={agent.id} className="p-2 border-b">
              <h4 className="font-bold">{agent.name}</h4>
              <p>{agent.description}</p>
              {/* Placeholder for invoking the agent */}
              <button className="px-4 py-2 mt-2 text-white bg-blue-500 rounded hover:bg-blue-600">
                Run Agent
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default AgentList;