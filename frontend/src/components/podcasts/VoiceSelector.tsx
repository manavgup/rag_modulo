import React, { useState, useRef, useEffect } from 'react';
import { PlayIcon, PauseIcon } from '@heroicons/react/24/solid';
import apiClient from '../../services/apiClient';
import { useNotification } from '../../contexts/NotificationContext';

interface VoiceOption {
  id: string;
  name: string;
  description: string;
}

interface VoiceSelectorProps {
  label: string;
  selectedVoice: string;
  onVoiceChange: (voiceId: string) => void;
  voiceOptions: VoiceOption[];
}

const VoiceSelector: React.FC<VoiceSelectorProps> = ({
  label,
  selectedVoice,
  onVoiceChange,
  voiceOptions,
}) => {
  const { addNotification } = useNotification();
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    // Cleanup audio on component unmount
    return () => {
      if (audioRef.current) {
        // Revoke blob URL to prevent memory leak
        if (audioRef.current.src && audioRef.current.src.startsWith('blob:')) {
          URL.revokeObjectURL(audioRef.current.src);
        }
        audioRef.current.pause();
        audioRef.current.src = '';
        audioRef.current = null;
      }
    };
  }, []);

  const handlePreview = async (voiceId: string) => {
    if (playingVoice === voiceId) {
      audioRef.current?.pause();
      setPlayingVoice(null);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
      // Revoke previous blob URL to prevent memory leak
      if (audioRef.current.src && audioRef.current.src.startsWith('blob:')) {
        URL.revokeObjectURL(audioRef.current.src);
      }
    }

    setPlayingVoice(voiceId);

    try {
      const audioBlob = await apiClient.getVoicePreview(voiceId);
      const audioUrl = URL.createObjectURL(audioBlob);

      if (!audioRef.current) {
        audioRef.current = new Audio();
      }
      audioRef.current.src = audioUrl;
      audioRef.current.play();

      audioRef.current.onended = () => {
        setPlayingVoice(null);
        URL.revokeObjectURL(audioUrl);
      };

      audioRef.current.onerror = () => {
        setPlayingVoice(null);
        URL.revokeObjectURL(audioUrl);
        addNotification('error', 'Playback Failed', 'Failed to play voice preview');
      };
    } catch (error) {
      console.error('Error playing voice preview:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addNotification('error', 'Preview Failed', `Could not load voice preview: ${errorMessage}`);
      setPlayingVoice(null);
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-white mb-2">{label}</label>
      <div className="space-y-2">
        {voiceOptions.map((voice) => (
          <div key={voice.id} className="flex items-center justify-between bg-gray-90 p-3 rounded-lg">
            <div className="flex items-center">
              <input
                type="radio"
                id={`${label}-${voice.id}`}
                name={label}
                value={voice.id}
                checked={selectedVoice === voice.id}
                onChange={() => onVoiceChange(voice.id)}
                className="w-4 h-4 text-blue-50 border-gray-30 rounded focus:ring-blue-50"
              />
              <label htmlFor={`${label}-${voice.id}`} className="ml-3">
                <span className="block text-sm font-medium text-white">{voice.name}</span>
                <span className="block text-xs text-gray-50">{voice.description}</span>
              </label>
            </div>
            <button
              onClick={() => handlePreview(voice.id)}
              className="p-2 rounded-full hover:bg-gray-800 transition-colors"
              aria-label={playingVoice === voice.id ? `Pause ${voice.name} preview` : `Play ${voice.name} preview`}
              aria-pressed={playingVoice === voice.id}
              title={playingVoice === voice.id ? `Pause ${voice.name} preview` : `Play ${voice.name} preview`}
            >
              {playingVoice === voice.id ? (
                <PauseIcon className="w-5 h-5 text-white" />
              ) : (
                <PlayIcon className="w-5 h-5 text-white" />
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default VoiceSelector;
