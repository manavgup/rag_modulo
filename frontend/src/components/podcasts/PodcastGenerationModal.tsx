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

// Default description template for script generation
const DEFAULT_DESCRIPTION = "Provide a comprehensive overview of the key topics, main insights, important concepts, and significant information from this collection. Focus on creating an engaging dialogue that educates listeners about the most valuable content.";

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
  const [duration, setDuration] = useState<number>(15);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState(DEFAULT_DESCRIPTION);
  const [format, setFormat] = useState<'mp3' | 'wav' | 'ogg' | 'flac'>('mp3');
  const [hostVoice, setHostVoice] = useState('alloy');
  const [expertVoice, setExpertVoice] = useState('onyx');
  const [includeIntro, setIncludeIntro] = useState(false);
  const [includeOutro, setIncludeOutro] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // New advanced options
  const [podcastStyle, setPodcastStyle] = useState('conversational_interview');
  const [language, setLanguage] = useState('en');
  const [complexityLevel, setComplexityLevel] = useState('intermediate');
  const [includeChapterMarkers, setIncludeChapterMarkers] = useState(false);
  const [generateTranscript, setGenerateTranscript] = useState(true);

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


  const estimatedCost = duration * 0.013; // $0.013 per minute for OpenAI TTS

  // Validation for button state
  const collectionId = providedCollectionId || selectedCollectionId;
  const isValid = collectionId && title.trim() && !isGenerating;

  const handleGenerate = async () => {
    const collectionId = providedCollectionId || selectedCollectionId;
    if (!collectionId) {
      addNotification('error', 'Validation Error', 'Please select a collection');
      return;
    }

    if (!title.trim()) {
      addNotification('error', 'Validation Error', 'Please provide a title for your podcast');
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
        title: title.trim(),
        description: description.trim() || undefined,
        format,
        host_voice: hostVoice,
        expert_voice: expertVoice,
        include_intro: includeIntro,
        include_outro: includeOutro,
        music_background: false,
        // New advanced options
        podcast_style: podcastStyle,
        language: language,
        complexity_level: complexityLevel,
        include_chapter_markers: includeChapterMarkers,
        generate_transcript: generateTranscript,
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
    <div className="fixed inset-0 bg-gray-100 bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-20">
          <div>
            <h2 className="text-base font-semibold text-gray-100">Generate Podcast</h2>
            {providedCollectionName && (
              <p className="text-xs text-gray-70 mt-1">From collection: {providedCollectionName}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-60 hover:text-gray-100"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-3 space-y-2">
          {/* Collection Selection (if not provided) */}
          {!providedCollectionId && (
            <div>
              <label className="block text-xs font-medium text-gray-100 mb-1">
                Collection *
              </label>
              {isLoadingCollections ? (
                <div className="text-gray-70 text-xs">Loading collections...</div>
              ) : (
                <select
                  value={selectedCollectionId}
                  onChange={(e) => setSelectedCollectionId(e.target.value)}
                  className="w-full px-2 py-1 text-xs border border-gray-30 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-60 focus:border-transparent"
                >
                  <option value="">Select a collection</option>
                  {collections.map((collection) => (
                    <option key={collection.id} value={collection.id}>
                      {collection.name}
                    </option>
                  ))}
                </select>
              )}
              <p className="text-xs text-gray-70 mt-1">
                Choose the collection to use as the knowledge base for your podcast
              </p>
            </div>
          )}

          {/* Duration Selection */}
          <div>
            <label className="block text-xs font-medium text-gray-100 mb-1">
              Duration: {duration} minutes
            </label>
            <div className="space-y-1">
              <input
                type="range"
                min="5"
                max="30"
                step="5"
                value={duration}
                onChange={(e) => setDuration(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-30 rounded-lg appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${((duration - 5) / (30 - 5)) * 100}%, #e5e7eb ${((duration - 5) / (30 - 5)) * 100}%, #e5e7eb 100%)`
                }}
              />
              <div className="flex justify-between text-xs text-gray-70">
                <span>5 min</span>
                <span>30 min</span>
              </div>
              <div className="text-xs text-gray-70">
                Cost: ${(duration * 0.013).toFixed(2)}
              </div>
            </div>
          </div>

          {/* Title (Required) */}
          <div>
            <label className="block text-xs font-medium text-gray-100 mb-1">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              placeholder="My Podcast Episode"
              required
              className="w-full px-2 py-1 text-xs border border-gray-30 rounded-lg text-gray-100 placeholder-gray-70 focus:outline-none focus:ring-2 focus:ring-blue-60 focus:border-transparent"
            />
            <p className="text-xs text-gray-70 mt-1">{title.length}/200 characters</p>
          </div>

          {/* Description (Script Prompt) */}
          <div>
            <label className="block text-xs font-medium text-gray-100 mb-1">
              Script Generation Prompt
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={1000}
              rows={5}
              placeholder={DEFAULT_DESCRIPTION}
              className="w-full px-2 py-1 text-xs border border-gray-30 rounded-lg text-gray-100 placeholder-gray-70 focus:outline-none focus:ring-2 focus:ring-blue-60 focus:border-transparent"
            />
            <p className="text-xs text-gray-70 mt-1">
              {description.length}/1000 characters. This prompt guides the AI in generating your podcast script.
            </p>
          </div>

          {/* Voice Settings */}
          <div className="grid grid-cols-2 gap-2">
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
          <div className="border border-gray-30 rounded-md">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full flex items-center justify-between px-3 py-2 text-sm text-blue-60 hover:text-blue-70 hover:bg-gray-10"
            >
              <div className="flex items-center space-x-2">
                <span className="font-medium">Advanced Options</span>
              </div>
              <svg
                className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showAdvanced && (
              <div className="border-t border-gray-30 p-3 space-y-4">
                {/* Format Selection */}
                <div>
                  <label className="block text-xs font-medium text-gray-100 mb-1">
                    Audio Format
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {FORMAT_OPTIONS.map((fmt) => (
                      <button
                        key={fmt.value}
                        onClick={() => setFormat(fmt.value as typeof format)}
                        className={`p-2 rounded border transition-all text-left ${
                          format === fmt.value
                            ? 'border-blue-60 bg-blue-60 bg-opacity-20'
                            : 'border-gray-30 hover:border-gray-40'
                        }`}
                      >
                        <div className="text-xs font-medium text-gray-100">{fmt.label}</div>
                        <div className="text-xs text-gray-70">{fmt.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Intro/Outro Options */}
                <div className="space-y-2">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={includeIntro}
                      onChange={(e) => setIncludeIntro(e.target.checked)}
                      className="w-4 h-4 text-blue-60 border-gray-30 rounded focus:ring-blue-60"
                    />
                    <span className="ml-2 text-xs text-gray-100">Include introduction segment</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={includeOutro}
                      onChange={(e) => setIncludeOutro(e.target.checked)}
                      className="w-4 h-4 text-blue-60 border-gray-30 rounded focus:ring-blue-60"
                    />
                    <span className="ml-2 text-xs text-gray-100">Include conclusion/outro segment</span>
                  </label>
                  <label className="flex items-center opacity-50 cursor-not-allowed">
                    <input
                      type="checkbox"
                      disabled
                      className="w-4 h-4 text-blue-60 border-gray-30 rounded"
                    />
                    <span className="ml-2 text-xs text-gray-70">Background music (coming soon)</span>
                  </label>
                </div>

                {/* New Advanced Options */}
                <div className="space-y-3">
                  <h4 className="text-xs font-medium text-gray-100">Content Options</h4>

                  {/* Podcast Style */}
                  <div>
                    <label className="block text-xs font-medium text-gray-100 mb-1">
                      Podcast Style
                    </label>
                    <select
                      value={podcastStyle}
                      onChange={(e) => setPodcastStyle(e.target.value)}
                      className="w-full px-2 py-1 text-xs border border-gray-30 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-60 focus:border-transparent"
                    >
                      <option value="conversational_interview">Conversational Interview</option>
                      <option value="narrative">Narrative</option>
                      <option value="educational">Educational</option>
                      <option value="discussion">Discussion</option>
                    </select>
                  </div>

                  {/* Language */}
                  <div>
                    <label className="block text-xs font-medium text-gray-100 mb-1">
                      Language
                    </label>
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="w-full px-2 py-1 text-xs border border-gray-30 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-60 focus:border-transparent"
                    >
                      <option value="en">English</option>
                      <option value="es">Spanish</option>
                      <option value="fr">French</option>
                      <option value="de">German</option>
                    </select>
                  </div>

                  {/* Complexity Level */}
                  <div>
                    <label className="block text-xs font-medium text-gray-100 mb-1">
                      Complexity Level
                    </label>
                    <select
                      value={complexityLevel}
                      onChange={(e) => setComplexityLevel(e.target.value)}
                      className="w-full px-2 py-1 text-xs border border-gray-30 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-60 focus:border-transparent"
                    >
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                    </select>
                  </div>

                  {/* Additional Options */}
                  <div className="space-y-2">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={includeChapterMarkers}
                        onChange={(e) => setIncludeChapterMarkers(e.target.checked)}
                        className="w-4 h-4 text-blue-60 border-gray-30 rounded focus:ring-blue-60"
                      />
                      <span className="ml-2 text-xs text-gray-100">Include chapter markers</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={generateTranscript}
                        onChange={(e) => setGenerateTranscript(e.target.checked)}
                        className="w-4 h-4 text-blue-60 border-gray-30 rounded focus:ring-blue-60"
                      />
                      <span className="ml-2 text-xs text-gray-100">Generate transcript</span>
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 p-3 border-t border-gray-20">
          <button
            onClick={onClose}
            disabled={isGenerating}
            className="px-3 py-1 text-xs text-gray-70 hover:text-gray-100 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleGenerate}
            disabled={!isValid}
            className="px-3 py-1 text-xs bg-blue-60 hover:bg-blue-70 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? 'Generating...' : 'Generate Podcast'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PodcastGenerationModal;
