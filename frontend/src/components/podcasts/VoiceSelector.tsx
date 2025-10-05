import React from 'react';
import { PlayIcon, PauseIcon } from '@heroicons/react/24/solid';

interface VoiceOption {
  id: string;
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
  onPlayPreview: (voiceId: string) => void;
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
  return (
    <div>
      <label className="block text-sm font-medium text-white mb-2">{label}</label>
      <div className="space-y-2">
        {options.map((voice) => {
          const isSelected = selectedVoice === voice.id;
          const isPlaying = playingVoiceId === voice.id;

          return (
            <div
              key={voice.id}
              onClick={() => onSelectVoice(voice.id)}
              className={`flex items-center justify-between p-3 rounded-lg border-2 cursor-pointer transition-all ${
                isSelected
                  ? 'border-blue-50 bg-blue-50 bg-opacity-20'
                  : 'border-gray-30 hover:border-gray-40'
              }`}
            >
              <div className="flex items-center">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (isPlaying) {
                      onStopPreview();
                    } else {
                      onPlayPreview(voice.id);
                    }
                  }}
                  className="mr-3 p-1 rounded-full bg-gray-90 hover:bg-gray-80 transition-colors"
                >
                  {isPlaying ? (
                    <PauseIcon className="w-5 h-5 text-white" />
                  ) : (
                    <PlayIcon className="w-5 h-5 text-white" />
                  )}
                </button>
                <div>
                  <div className="font-medium text-white">{voice.name}</div>
                  <div className="text-sm text-gray-50">{voice.description}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default VoiceSelector;