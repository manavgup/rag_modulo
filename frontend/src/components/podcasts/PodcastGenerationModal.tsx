import React, { useState, useRef, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import apiClient, { PodcastGenerationInput, VoiceId } from '../../services/apiClient';
import VoiceSelector from './VoiceSelector';

interface PodcastGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  collectionId?: string;
  collectionName?: string;
  onPodcastCreated?: (podcastId: string) => void;
}

const VOICE_OPTIONS: Array<{id: VoiceId; name: string; gender: 'male' | 'female' | 'neutral'; description: string}> = [
  { id: 'alloy', name: 'Alloy', gender: 'neutral', description: 'Neutral, balanced voice' },
  { id: 'echo', name: 'Echo', gender: 'male', description: 'Warm, articulate male voice' },
  { id: 'fable', name: 'Fable', gender: 'neutral', description: 'Expressive, storytelling voice' },
  { id: 'onyx', name: 'Onyx', gender: 'male', description: 'Deep, authoritative male voice' },
  { id: 'nova', name: 'Nova', gender: 'female', description: 'Energetic, clear female voice' },
  { id: 'shimmer', name: 'Shimmer', gender: 'female', description: 'Soft, friendly female voice' },
];

const DURATION_OPTIONS = [
  { value: 5, label: '5 minutes', cost: 0.07 },
  { value: 15, label: '15 minutes', cost: 0.20 },
  { value: 30, label: '30 minutes', cost: 0.41 },
  { value: 60, label: '60 minutes', cost: 0.81 },
];

const FORMAT_OPTIONS = [
  { value: 'mp3', label: 'MP3', description: 'Standard format, widely supported' },
  { value: 'wav', label: 'WAV', description: 'Uncompressed, high quality' },
  { value: 'ogg', label: 'OGG', description: 'Open format, good quality' },
  { value: 'flac', label: 'FLAC', description: 'Lossless compression' },
];

const PodcastGenerationModal: React.FC<PodcastGenerationModalProps> = ({
  isOpen,
  onClose,
  collectionId: providedCollectionId,
  collectionName: providedCollectionName,
  onPodcastCreated,
}) => {
  const { addNotification } = useNotification();
  const [isGenerating, setIsGenerating] = useState(false);
  const [duration, setDuration] = useState<5 | 15 | 30 | 60>(15);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [format, setFormat] = useState<'mp3' | 'wav' | 'ogg' | 'flac'>('mp3');
  const [hostVoice, setHostVoice] = useState('alloy');
  const [expertVoice, setExpertVoice] = useState('onyx');
  const [includeIntro, setIncludeIntro] = useState(false);
  const [includeOutro, setIncludeOutro] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Collection selection state (when collection not provided)
  const [collections, setCollections] = useState<Array<{id: string; name: string}>>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<string>(providedCollectionId || '');
  const [isLoadingCollections, setIsLoadingCollections] = useState(false);

  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const handlePlayPreview = async (voiceId: VoiceId) => {
    if (playingVoiceId === voiceId) {
      handleStopPreview();
      return;
    }

    try {
      const audioBlob = await apiClient.getVoicePreview(voiceId);
      const audioUrl = URL.createObjectURL(audioBlob);

      // Clean up previous audio if exists
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
      }
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }

      audioUrlRef.current = audioUrl;
      audioRef.current = new Audio(audioUrl);
      audioRef.current.play();
      setPlayingVoiceId(voiceId);

      audioRef.current.onended = () => {
        setPlayingVoiceId(null);
      };
    } catch (error) {
      console.error('Error playing voice preview:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addNotification('error', 'Preview Failed', `Could not load voice preview: ${errorMessage}`);
    }
  };

  const handleStopPreview = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setPlayingVoiceId(null);
  };

  useEffect(() => {
    return () => {
      // Cleanup audio on component unmount
      handleStopPreview();
    };
  }, []);

  // Load collections when modal opens and no collection is provided
  useEffect(() => {
    if (isOpen && !providedCollectionId) {
      loadCollections();
    }
  }, [isOpen, providedCollectionId]);

  const loadCollections = async () => {
    setIsLoadingCollections(true);
    try {
      const collectionsData = await apiClient.getCollections();
      setCollections(collectionsData.map(c => ({ id: c.id, name: c.name })));
    } catch (error) {
      console.error('Error loading collections:', error);
      addNotification('error', 'Load Failed', 'Failed to load collections');
    } finally {
      setIsLoadingCollections(false);
    }
  };


  const selectedDuration = DURATION_OPTIONS.find(d => d.value === duration);
  const estimatedCost = selectedDuration?.cost || 0;

  const handleGenerate = async () => {
    const collectionId = providedCollectionId || selectedCollectionId;
    if (!collectionId) {
      addNotification('error', 'Validation Error', 'Please select a collection');
      return;
    }

    setIsGenerating(true);
    try {
      const input: PodcastGenerationInput = {
        collection_id: collectionId,
        duration,
        voice_settings: {
          voice_id: hostVoice,
          speed: 1.0,
          pitch: 1.0,
        },
        title: title.trim() || undefined,
        description: description.trim() || undefined,
        format,
        host_voice: hostVoice,
        expert_voice: expertVoice,
        include_intro: includeIntro,
        include_outro: includeOutro,
        music_background: false,
      };

      const podcast = await apiClient.generatePodcast(input);

      addNotification(
        'success',
        'Podcast Generation Started',
        `Your podcast is being generated. This may take 1-2 minutes.`
      );

      if (onPodcastCreated) {
        onPodcastCreated(podcast.podcast_id);
      }

      onClose();
    } catch (error: any) {
      console.error('Error generating podcast:', error);
      addNotification(
        'error',
        'Generation Failed',
        error.response?.data?.detail || 'Failed to start podcast generation.'
      );
    } finally {
      setIsGenerating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-gray-100 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-30">
          <div>
            <h2 className="text-2xl font-semibold text-white">Generate Podcast</h2>
            {providedCollectionName && (
              <p className="text-gray-50 mt-1">From collection: {providedCollectionName}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-50 hover:text-white transition-colors"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6">
          {/* Collection Selection (if not provided) */}
          {!providedCollectionId && (
            <div>
              <label className="block text-sm font-medium text-white mb-3">
                Collection *
              </label>
              {isLoadingCollections ? (
                <div className="text-gray-50 text-sm">Loading collections...</div>
              ) : (
                <select
                  value={selectedCollectionId}
                  onChange={(e) => setSelectedCollectionId(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-90 border border-gray-30 rounded-lg text-white focus:outline-none focus:border-blue-50"
                >
                  <option value="">Select a collection</option>
                  {collections.map((collection) => (
                    <option key={collection.id} value={collection.id}>
                      {collection.name}
                    </option>
                  ))}
                </select>
              )}
              <p className="text-xs text-gray-50 mt-1">
                Choose the collection to use as the knowledge base for your podcast
              </p>
            </div>
          )}

          {/* Duration Selection */}
          <div>
            <label className="block text-sm font-medium text-white mb-3">
              Duration
            </label>
            <div className="grid grid-cols-4 gap-3">
              {DURATION_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setDuration(option.value as 5 | 15 | 30 | 60)}
                  className={`p-3 rounded-lg border-2 transition-all ${
                    duration === option.value
                      ? 'border-blue-50 bg-blue-50 bg-opacity-20 text-white'
                      : 'border-gray-30 text-gray-50 hover:border-gray-40'
                  }`}
                >
                  <div className="text-sm font-medium">{option.label}</div>
                  <div className="text-xs mt-1">${option.cost.toFixed(2)}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Title (Optional) */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Title <span className="text-gray-50">(optional)</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              placeholder="My Podcast Episode"
              className="w-full px-4 py-2 bg-gray-90 border border-gray-30 rounded-lg text-white placeholder-gray-50 focus:outline-none focus:border-blue-50"
            />
            <p className="text-xs text-gray-50 mt-1">{title.length}/200 characters</p>
          </div>

          {/* Description (Optional) */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Description <span className="text-gray-50">(optional)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={500}
              rows={3}
              placeholder="Brief description of your podcast..."
              className="w-full px-4 py-2 bg-gray-90 border border-gray-30 rounded-lg text-white placeholder-gray-50 focus:outline-none focus:border-blue-50"
            />
            <p className="text-xs text-gray-50 mt-1">{description.length}/500 characters</p>
          </div>

          {/* Voice Settings */}
          <div className="grid grid-cols-2 gap-4">
            <VoiceSelector
              label="Host Voice"
              options={VOICE_OPTIONS}
              selectedVoice={hostVoice}
              onSelectVoice={setHostVoice}
              playingVoiceId={playingVoiceId}
              onPlayPreview={handlePlayPreview}
              onStopPreview={handleStopPreview}
            />
            <VoiceSelector
              label="Expert Voice"
              options={VOICE_OPTIONS}
              selectedVoice={expertVoice}
              onSelectVoice={setExpertVoice}
              playingVoiceId={playingVoiceId}
              onPlayPreview={handlePlayPreview}
              onStopPreview={handleStopPreview}
            />
          </div>

          {/* Advanced Options (Collapsible) */}
          <div>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center text-blue-50 hover:text-blue-40 transition-colors"
            >
              <span className="text-sm font-medium">Advanced Options</span>
              <svg
                className={`w-4 h-4 ml-2 transition-transform ${showAdvanced ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showAdvanced && (
              <div className="mt-4 space-y-4 p-4 bg-gray-90 rounded-lg">
                {/* Format Selection */}
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    Audio Format
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {FORMAT_OPTIONS.map((fmt) => (
                      <button
                        key={fmt.value}
                        onClick={() => setFormat(fmt.value as typeof format)}
                        className={`p-2 rounded border transition-all text-left ${
                          format === fmt.value
                            ? 'border-blue-50 bg-blue-50 bg-opacity-20'
                            : 'border-gray-30 hover:border-gray-40'
                        }`}
                      >
                        <div className="text-sm font-medium text-white">{fmt.label}</div>
                        <div className="text-xs text-gray-50">{fmt.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Intro/Outro Options */}
                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={includeIntro}
                      onChange={(e) => setIncludeIntro(e.target.checked)}
                      className="w-4 h-4 text-blue-50 border-gray-30 rounded focus:ring-blue-50"
                    />
                    <span className="ml-2 text-sm text-white">Include introduction segment</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={includeOutro}
                      onChange={(e) => setIncludeOutro(e.target.checked)}
                      className="w-4 h-4 text-blue-50 border-gray-30 rounded focus:ring-blue-50"
                    />
                    <span className="ml-2 text-sm text-white">Include conclusion/outro segment</span>
                  </label>
                  <label className="flex items-center opacity-50 cursor-not-allowed">
                    <input
                      type="checkbox"
                      disabled
                      className="w-4 h-4 text-blue-50 border-gray-30 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-50">Background music (coming soon)</span>
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Cost Estimate */}
          <div className="bg-blue-50 bg-opacity-10 border border-blue-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-white">Estimated Cost</h3>
                <p className="text-xs text-gray-50 mt-1">OpenAI TTS API usage</p>
              </div>
              <div className="text-2xl font-bold text-blue-50">
                ${estimatedCost.toFixed(2)}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-30">
          <button
            onClick={onClose}
            disabled={isGenerating}
            className="px-4 py-2 text-gray-50 hover:text-white transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="px-6 py-2 bg-blue-50 hover:bg-blue-40 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? 'Generating...' : 'Generate Podcast'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PodcastGenerationModal;
