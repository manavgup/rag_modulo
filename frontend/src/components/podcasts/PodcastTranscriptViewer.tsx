import React, { useState } from 'react';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

interface PodcastTranscriptViewerProps {
  transcript: string;
  currentTime?: number;
}

const PodcastTranscriptViewer: React.FC<PodcastTranscriptViewerProps> = ({
  transcript,
  currentTime = 0,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  // Parse transcript into turns (HOST: ... / EXPERT: ...)
  const parseTurns = () => {
    const lines = transcript.split('\n');
    const turns: Array<{ speaker: string; text: string }> = [];
    let currentSpeaker = '';
    let currentText = '';

    for (const line of lines) {
      const hostMatch = line.match(/^(HOST|Host):\s*(.+)$/);
      const expertMatch = line.match(/^(EXPERT|Expert):\s*(.+)$/);

      if (hostMatch) {
        if (currentSpeaker && currentText) {
          turns.push({ speaker: currentSpeaker, text: currentText.trim() });
        }
        currentSpeaker = 'HOST';
        currentText = hostMatch[2];
      } else if (expertMatch) {
        if (currentSpeaker && currentText) {
          turns.push({ speaker: currentSpeaker, text: currentText.trim() });
        }
        currentSpeaker = 'EXPERT';
        currentText = expertMatch[2];
      } else if (line.trim() && currentSpeaker) {
        currentText += ' ' + line.trim();
      }
    }

    if (currentSpeaker && currentText) {
      turns.push({ speaker: currentSpeaker, text: currentText.trim() });
    }

    return turns;
  };

  const turns = parseTurns();

  const highlightText = (text: string) => {
    if (!searchTerm.trim()) return text;

    const parts = text.split(new RegExp(`(${searchTerm})`, 'gi'));
    return parts.map((part, index) =>
      part.toLowerCase() === searchTerm.toLowerCase() ? (
        <mark key={index} className="bg-yellow-30 text-gray-100">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  const filteredTurns = turns.filter((turn) =>
    searchTerm.trim() === '' ||
    turn.text.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="bg-gray-10 border border-gray-20 rounded-lg">
      {/* Search Header */}
      <div className="p-4 border-b border-gray-20">
        <div className="flex items-center gap-2">
          <MagnifyingGlassIcon className="w-5 h-5 text-gray-70" />
          <input
            type="text"
            placeholder="Search transcript..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 px-3 py-2 bg-white border border-gray-20 rounded-lg text-gray-100 placeholder-gray-60 focus:outline-none focus:border-blue-60"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="text-gray-70 hover:text-gray-100 text-sm transition-colors"
            >
              Clear
            </button>
          )}
        </div>
        {searchTerm && (
          <div className="text-xs text-gray-70 mt-2">
            {filteredTurns.length} result{filteredTurns.length !== 1 ? 's' : ''} found
          </div>
        )}
      </div>

      {/* Transcript Content */}
      <div className="p-4 max-h-[600px] overflow-y-auto">
        {filteredTurns.length === 0 ? (
          <div className="text-center py-8 text-gray-70">
            {searchTerm ? 'No matches found' : 'No transcript available'}
          </div>
        ) : (
          <div className="space-y-4">
            {filteredTurns.map((turn, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg ${
                  turn.speaker === 'HOST'
                    ? 'bg-blue-60 bg-opacity-10 border-l-4 border-blue-60'
                    : 'bg-purple-50 bg-opacity-10 border-l-4 border-purple-50'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      turn.speaker === 'HOST'
                        ? 'bg-blue-60 text-white'
                        : 'bg-purple-50 text-white'
                    }`}
                  >
                    {turn.speaker}
                  </span>
                </div>
                <div className="text-sm text-gray-100 leading-relaxed">
                  {highlightText(turn.text)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stats Footer */}
      <div className="p-3 border-t border-gray-20 flex items-center justify-between text-xs text-gray-70">
        <span>{turns.length} dialogue turns</span>
        <span>{transcript.split(' ').length} words</span>
      </div>
    </div>
  );
};

export default PodcastTranscriptViewer;
