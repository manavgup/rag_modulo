import React from 'react';
import SourceCard, { Source } from './SourceCard';

interface SourceListProps {
  sources: Source[];
}

const SourceList: React.FC<SourceListProps> = ({ sources }) => {
  if (!sources || sources.length === 0) {
    return (
      <div className="text-center py-4 text-sm text-gray-500">
        No sources found for this response.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {sources.map((source, index) => (
        <SourceCard key={`${source.document_name}-${index}`} source={source} />
      ))}
    </div>
  );
};

export default SourceList;