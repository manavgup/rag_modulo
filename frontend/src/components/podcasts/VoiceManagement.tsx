import React, { useState, useEffect, useRef } from 'react';
import { PlayIcon, PauseIcon, TrashIcon, CloudArrowUpIcon, CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import apiClient, { CustomVoice, VoiceUploadInput } from '../../services/apiClient';

const VoiceManagement: React.FC = () => {
  const { addNotification } = useNotification();
  const [voices, setVoices] = useState<CustomVoice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  // Upload form state
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploadGender, setUploadGender] = useState<'male' | 'female' | 'neutral'>('neutral');
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  useEffect(() => {
    loadVoices();
    // Poll for status updates every 5 seconds
    const interval = setInterval(loadVoices, 5000);
    return () => {
      clearInterval(interval);
      handleStopPreview();
    };
  }, []);

  const loadVoices = async () => {
    try {
      const response = await apiClient.listVoices(100, 0);
      setVoices(response.voices);
    } catch (error) {
      console.error('Error loading voices:', error);
      if (!isLoading) { // Don't show error on initial load
        addNotification('error', 'Load Failed', 'Failed to load custom voices');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const ext = file.name.split('.').pop()?.toLowerCase();

      if (!['mp3', 'wav', 'm4a', 'flac', 'ogg'].includes(ext || '')) {
        addNotification('error', 'Invalid Format', 'Please select an MP3, WAV, M4A, FLAC, or OGG file');
        return;
      }

      if (file.size > 10 * 1024 * 1024) { // 10MB
        addNotification('error', 'File Too Large', 'Voice sample must be under 10MB');
        return;
      }

      setUploadFile(file);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!uploadFile || !uploadName.trim()) {
      addNotification('error', 'Validation Error', 'Please provide a name and select a file');
      return;
    }

    setIsUploading(true);
    try {
      const input: VoiceUploadInput = {
        name: uploadName.trim(),
        description: uploadDescription.trim() || undefined,
        gender: uploadGender,
      };

      const voice = await apiClient.uploadVoice(input, uploadFile);

      addNotification('success', 'Upload Complete', `Voice "${voice.name}" uploaded successfully`);

      // Auto-process with ElevenLabs
      try {
        await apiClient.processVoice(voice.voice_id, 'elevenlabs');
        addNotification('info', 'Processing Started', 'Your voice is being processed. This may take 30-60 seconds.');
      } catch (processError) {
        console.error('Error processing voice:', processError);
        addNotification('warning', 'Processing Delayed', 'Voice uploaded but processing failed. Please try again.');
      }

      // Reset form and reload
      setShowUploadForm(false);
      setUploadName('');
      setUploadDescription('');
      setUploadGender('neutral');
      setUploadFile(null);
      await loadVoices();
    } catch (error: any) {
      console.error('Error uploading voice:', error);
      addNotification(
        'error',
        'Upload Failed',
        error.response?.data?.detail || 'Failed to upload voice sample'
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handlePlayPreview = async (voice: CustomVoice) => {
    if (playingVoiceId === voice.voice_id) {
      handleStopPreview();
      return;
    }

    if (voice.status !== 'ready') {
      addNotification('info', 'Voice Not Ready', 'This voice is still processing');
      return;
    }

    try {
      const audioBlob = await apiClient.getVoiceSample(voice.voice_id);
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
      setPlayingVoiceId(voice.voice_id);

      audioRef.current.onended = () => {
        setPlayingVoiceId(null);
      };
    } catch (error) {
      console.error('Error playing voice preview:', error);
      addNotification('error', 'Preview Failed', 'Could not load voice preview');
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

  const handleDelete = async (voice: CustomVoice) => {
    if (!window.confirm(`Delete voice "${voice.name}"? This cannot be undone.`)) {
      return;
    }

    try {
      await apiClient.deleteVoice(voice.voice_id);
      addNotification('success', 'Voice Deleted', `Voice "${voice.name}" has been deleted`);
      await loadVoices();
    } catch (error: any) {
      console.error('Error deleting voice:', error);
      addNotification(
        'error',
        'Delete Failed',
        error.response?.data?.detail || 'Failed to delete voice'
      );
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'processing':
      case 'uploading':
        return <ClockIcon className="w-5 h-5 text-yellow-500 animate-spin" />;
      case 'failed':
        return <XCircleIcon className="w-5 h-5 text-red-500" />;
      default:
        return null;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-70">Loading voices...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Custom Voices</h1>
          <p className="text-sm text-gray-70 mt-1">
            Upload and manage custom voices for podcast generation
          </p>
        </div>
        <button
          onClick={() => setShowUploadForm(!showUploadForm)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-60 hover:bg-blue-70 text-white rounded-lg transition-colors"
        >
          <CloudArrowUpIcon className="w-5 h-5" />
          Upload Voice
        </button>
      </div>

      {/* Upload Form */}
      {showUploadForm && (
        <form onSubmit={handleUpload} className="bg-white border border-gray-30 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-100 mb-4">Upload New Voice</h2>

          <div className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-100 mb-1">
                Voice Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={uploadName}
                onChange={(e) => setUploadName(e.target.value)}
                maxLength={200}
                placeholder="e.g., John's Voice"
                required
                className="w-full px-3 py-2 text-sm border border-gray-30 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-60"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-100 mb-1">
                Description (Optional)
              </label>
              <textarea
                value={uploadDescription}
                onChange={(e) => setUploadDescription(e.target.value)}
                maxLength={1000}
                rows={2}
                placeholder="Describe the voice characteristics..."
                className="w-full px-3 py-2 text-sm border border-gray-30 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-60"
              />
            </div>

            {/* Gender */}
            <div>
              <label className="block text-sm font-medium text-gray-100 mb-1">
                Gender Classification
              </label>
              <select
                value={uploadGender}
                onChange={(e) => setUploadGender(e.target.value as 'male' | 'female' | 'neutral')}
                className="w-full px-3 py-2 text-sm border border-gray-30 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-60"
              >
                <option value="neutral">Neutral</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>
            </div>

            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-100 mb-1">
                Audio File <span className="text-red-500">*</span>
              </label>
              <input
                type="file"
                accept=".mp3,.wav,.m4a,.flac,.ogg"
                onChange={handleFileSelect}
                className="w-full px-3 py-2 text-sm border border-gray-30 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-60"
              />
              <p className="text-xs text-gray-70 mt-1">
                Supported: MP3, WAV, M4A, FLAC, OGG • Max: 10MB • Recommended: 5 seconds to 5 minutes
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 mt-6">
            <button
              type="submit"
              disabled={isUploading || !uploadFile || !uploadName.trim()}
              className="px-4 py-2 bg-blue-60 hover:bg-blue-70 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? 'Uploading...' : 'Upload & Process'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowUploadForm(false);
                setUploadName('');
                setUploadDescription('');
                setUploadGender('neutral');
                setUploadFile(null);
              }}
              disabled={isUploading}
              className="px-4 py-2 text-gray-70 hover:text-gray-100 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Voices List */}
      <div className="space-y-4">
        {voices.length === 0 ? (
          <div className="bg-gray-10 border border-gray-30 rounded-lg p-8 text-center">
            <CloudArrowUpIcon className="w-12 h-12 text-gray-60 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-100 mb-1">No custom voices yet</h3>
            <p className="text-sm text-gray-70 mb-4">
              Upload a voice sample to create custom voices for your podcasts
            </p>
            <button
              onClick={() => setShowUploadForm(true)}
              className="px-4 py-2 bg-blue-60 hover:bg-blue-70 text-white rounded-lg transition-colors"
            >
              Upload Your First Voice
            </button>
          </div>
        ) : (
          voices.map((voice) => (
            <div
              key={voice.voice_id}
              className="bg-white border border-gray-30 rounded-lg p-4 hover:border-gray-40 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-base font-semibold text-gray-100">{voice.name}</h3>
                    {getStatusIcon(voice.status)}
                    <span className="text-xs text-gray-70 capitalize">{voice.status}</span>
                    {voice.quality_score && (
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                        Quality: {voice.quality_score}/100
                      </span>
                    )}
                  </div>
                  {voice.description && (
                    <p className="text-sm text-gray-70 mb-2">{voice.description}</p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-gray-70">
                    <span>Gender: {voice.gender}</span>
                    <span>Size: {formatFileSize(voice.sample_file_size)}</span>
                    <span>Provider: {voice.provider_name || 'Not processed'}</span>
                    {voice.times_used > 0 && <span>Used {voice.times_used}x</span>}
                  </div>
                  {voice.error_message && (
                    <div className="mt-2 text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                      Error: {voice.error_message}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 ml-4">
                  {voice.status === 'ready' && (
                    <button
                      onClick={() => handlePlayPreview(voice)}
                      className="p-2 rounded-full bg-gray-20 hover:bg-gray-30 transition-colors"
                      title="Play preview"
                    >
                      {playingVoiceId === voice.voice_id ? (
                        <PauseIcon className="w-5 h-5 text-gray-70" />
                      ) : (
                        <PlayIcon className="w-5 h-5 text-gray-70" />
                      )}
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(voice)}
                    className="p-2 rounded-full bg-red-50 hover:bg-red-100 transition-colors"
                    title="Delete voice"
                  >
                    <TrashIcon className="w-5 h-5 text-red-600" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Info Card */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-blue-900 mb-2">Tips for Best Results</h4>
        <ul className="text-xs text-blue-800 space-y-1">
          <li>• Use clear audio with minimal background noise</li>
          <li>• Recommended duration: 5 seconds to 5 minutes</li>
          <li>• Speak naturally at your normal pace</li>
          <li>• Processing typically takes 30-60 seconds</li>
          <li>• Once "Ready", voices can be used in podcast generation</li>
        </ul>
      </div>
    </div>
  );
};

export default VoiceManagement;
