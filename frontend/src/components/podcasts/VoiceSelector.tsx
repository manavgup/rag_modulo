import React, { useState } from 'react';
import { PlayIcon, PauseIcon, ChevronDownIcon } from '@heroicons/react/24/solid';
import { VoiceId } from '../../services/apiClient';

interface VoiceOption {
  id: VoiceId;
  name: string;
  gender: 'male' | 'female' | 'neutral';
  description: string;
}

interface VoiceSelectorProps {
  label: string;
  options: VoiceOption[];
  selectedVoice: string;
  onSelectVoice: (voiceId: string) => void;
  playingVoiceId: string | null;
  onPlayPreview: (voiceId: VoiceId) => void | Promise<void>;
  onStopPreview: () => void;
}

const VoiceSelector: React.FC<VoiceSelectorProps> = ({
  label,
  options,
  selectedVoice,
  onSelectVoice,
  playingVoiceId,
  onPlayPreview,
  onStopPreview,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const selectedOption = options.find(option => option.id === selectedVoice);

  const handleVoiceSelect = (voiceId: string) => {
    onSelectVoice(voiceId);
    setIsOpen(false);
  };

  const handlePlayClick = (e: React.MouseEvent, voiceId: VoiceId) => {
    e.stopPropagation();
    if (playingVoiceId === voiceId) {
      onStopPreview();
    } else {
      onPlayPreview(voiceId);
    }
  };

  return (
    <div className="relative">
      <label className="block text-xs font-medium text-gray-100 mb-1">{label}</label>

      {/* Dropdown Button */}
      <div
        className="relative w-full px-2 py-1 text-xs border border-gray-30 rounded-lg cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-60 focus:border-transparent"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <button
              onClick={(e) => handlePlayClick(e, selectedVoice as VoiceId)}
              className="mr-2 p-1 rounded-full bg-gray-20 hover:bg-gray-30 transition-colors"
            >
              {playingVoiceId === selectedVoice ? (
                <PauseIcon className="w-3 h-3 text-gray-70" />
              ) : (
                <PlayIcon className="w-3 h-3 text-gray-70" />
              )}
            </button>
            <div>
              <div className="font-medium text-gray-100 text-xs">{selectedOption?.name}</div>
              <div className="text-xs text-gray-70">{selectedOption?.description}</div>
            </div>
          </div>
          <ChevronDownIcon className={`w-4 h-4 text-gray-70 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-30 rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {options.map((voice) => {
            const isPlaying = playingVoiceId === voice.id;

            return (
              <div
                key={voice.id}
                onClick={() => handleVoiceSelect(voice.id)}
                className="flex items-center justify-between px-2 py-1 hover:bg-gray-20 cursor-pointer transition-colors"
              >
                <div className="flex items-center">
                  <button
                    onClick={(e) => handlePlayClick(e, voice.id)}
                    className="mr-2 p-1 rounded-full bg-gray-20 hover:bg-gray-30 transition-colors"
                  >
                    {isPlaying ? (
                      <PauseIcon className="w-3 h-3 text-gray-70" />
                    ) : (
                      <PlayIcon className="w-3 h-3 text-gray-70" />
                    )}
                  </button>
                  <div>
                    <div className="font-medium text-gray-100 text-xs">{voice.name}</div>
                    <div className="text-xs text-gray-70">{voice.description}</div>
                  </div>
                </div>
                {selectedVoice === voice.id && (
                  <div className="w-2 h-2 bg-blue-60 rounded-full"></div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default VoiceSelector;
