import React, { useState } from 'react';
import {
  XMarkIcon,
  DocumentIcon,
  FolderIcon,
  ExclamationTriangleIcon,
  CloudArrowUpIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import apiClient from '../../services/apiClient';

interface CreateCollectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCollectionCreated: (collection: any) => void;
}

interface FormData {
  name: string;
  visibility: 'private' | 'public';
}

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'pending' | 'uploading' | 'complete' | 'error';
  progress: number;
}

const LightweightCreateCollectionModal: React.FC<CreateCollectionModalProps> = ({
  isOpen,
  onClose,
  onCollectionCreated,
}) => {
  const { addNotification } = useNotification();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  const [formData, setFormData] = useState<FormData>({
    name: '',
    visibility: 'private',
  });

  const resetForm = () => {
    setFormData({
      name: '',
      visibility: 'private',
    });
    setUploadedFiles([]);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);

    files.forEach(file => {
      const uploadedFile: UploadedFile = {
        id: Date.now().toString() + Math.random().toString(36),
        name: file.name,
        size: file.size,
        type: file.type,
        status: 'pending',
        progress: 0,
      };

      setUploadedFiles(prev => [...prev, uploadedFile]);

      // Simulate upload progress
      simulateUpload(uploadedFile.id);
    });
  };

  const simulateUpload = (fileId: string) => {
    setUploadedFiles(prev => prev.map(file =>
      file.id === fileId ? { ...file, status: 'uploading' } : file
    ));

    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 20;

      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);

        setUploadedFiles(prev => prev.map(file =>
          file.id === fileId ? { ...file, status: 'complete', progress: 100 } : file
        ));
      } else {
        setUploadedFiles(prev => prev.map(file =>
          file.id === fileId ? { ...file, progress } : file
        ));
      }
    }, 200);
  };

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(file => file.id !== fileId));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateForm = () => {
    return formData.name.trim().length > 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setIsSubmitting(true);

    try {
      const newCollection = await apiClient.createCollection({
        name: formData.name,
        description: `Collection with ${formData.visibility} visibility`
      });

      onCollectionCreated(newCollection);
      addNotification('success', 'Collection Created', `"${formData.name}" has been created successfully.`);
      handleClose();
    } catch (error) {
      console.error('Error creating collection:', error);
      addNotification('error', 'Creation Failed', 'Failed to create collection. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-100 bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-screen overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-20">
          <div>
            <h2 className="text-xl font-semibold text-gray-100">Create New Collection</h2>
            <p className="text-sm text-gray-70">Create a collection to organize your documents</p>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-60 hover:text-gray-100"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Collection Name */}
          <div>
            <label className="block text-sm font-medium text-gray-100 mb-2">
              Collection Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              placeholder="Enter collection name"
              className="input-field w-full"
              autoFocus
            />
          </div>

          {/* Privacy Settings */}
          <div>
            <label className="block text-sm font-medium text-gray-100 mb-3">
              Privacy
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { value: 'private', icon: '🔒', title: 'Private', desc: 'Only you can access this collection' },
                { value: 'public', icon: '🌐', title: 'Public', desc: 'Anyone can access this collection' },
              ].map((option) => (
                <div key={option.value} className="cursor-pointer">
                  <input
                    type="radio"
                    name="visibility"
                    value={option.value}
                    checked={formData.visibility === option.value}
                    onChange={(e) => handleInputChange('visibility', e.target.value as 'private' | 'public')}
                    className="sr-only"
                    id={`visibility-${option.value}`}
                  />
                  <label
                    htmlFor={`visibility-${option.value}`}
                    className={`block p-4 border-2 rounded-lg text-center transition-colors cursor-pointer ${
                      formData.visibility === option.value
                        ? 'border-blue-60 bg-blue-10'
                        : 'border-gray-20 hover:border-gray-30'
                    }`}
                    style={{
                      borderColor: formData.visibility === option.value ? '#1D4ED8' : '#E5E7EB',
                      backgroundColor: formData.visibility === option.value ? '#DBEAFE' : 'white',
                      borderWidth: '2px'
                    }}
                  >
                    <div className="text-2xl mb-2">{option.icon}</div>
                    <div className="font-medium text-gray-100">{option.title}</div>
                    <div className="text-xs text-gray-70 mt-1">{option.desc}</div>
                  </label>
                </div>
              ))}
            </div>
          </div>

          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-100 mb-3">
              Upload Files (Optional)
            </label>

            {/* Upload Area */}
            <div
              className="border-2 border-dashed border-gray-30 rounded-lg p-8 text-center hover:border-blue-60 transition-colors cursor-pointer"
              onClick={() => document.getElementById('file-upload')?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const files = Array.from(e.dataTransfer.files);
                const event = { target: { files } } as any;
                handleFileUpload(event);
              }}
            >
              <CloudArrowUpIcon className="w-12 h-12 text-gray-60 mx-auto mb-4" />
              <p className="text-gray-100 mb-2">Drag and drop files here</p>
              <p className="text-sm text-gray-70 mb-4">or click to select files</p>
              <input
                type="file"
                multiple
                onChange={handleFileUpload}
                accept=".pdf,.docx,.txt,.md"
                className="hidden"
                id="file-upload"
              />
              <div className="btn-primary cursor-pointer inline-block">
                Select Files
              </div>
              <p className="text-xs text-gray-60 mt-3">
                Supported formats: PDF, DOCX, TXT, MD (max 100MB per file)
              </p>
            </div>

            {/* File List */}
            {uploadedFiles.length > 0 && (
              <div className="mt-4 space-y-3">
                <h4 className="font-medium text-gray-100">Uploaded Files ({uploadedFiles.length})</h4>
                <div className="max-h-40 overflow-y-auto space-y-2">
                  {uploadedFiles.map((file) => (
                    <div key={file.id} className="flex items-center space-x-3 p-3 border border-gray-20 rounded-lg">
                      <DocumentIcon className="w-5 h-5 text-gray-60 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-100 truncate">{file.name}</p>
                        <p className="text-xs text-gray-60">{formatFileSize(file.size)}</p>
                        {file.status === 'uploading' && (
                          <div className="w-full bg-gray-20 rounded-full h-1 mt-1">
                            <div
                              className="bg-blue-60 h-1 rounded-full transition-all duration-300"
                              style={{ width: `${file.progress}%` }}
                            />
                          </div>
                        )}
                      </div>
                      <div className="flex items-center space-x-2">
                        {file.status === 'error' && (
                          <ExclamationTriangleIcon className="w-4 h-4 text-red-50" />
                        )}
                        <button
                          onClick={() => removeFile(file.id)}
                          className="text-gray-60 hover:text-red-50"
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 px-6 py-4 border-t border-gray-20">
          <button
            onClick={handleClose}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!validateForm() || isSubmitting}
            className="btn-primary disabled:opacity-50 flex items-center space-x-2"
          >
            {isSubmitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                <span>Creating...</span>
              </>
            ) : (
              <>
                <FolderIcon className="w-4 h-4" />
                <span>Create Collection</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LightweightCreateCollectionModal;
