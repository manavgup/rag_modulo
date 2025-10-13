import React, { useState } from 'react';
import { CloudArrowUpIcon, DocumentIcon, TrashIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'pending' | 'uploading' | 'complete' | 'error';
  progress: number;
  file: File;
}

export interface FileUploadProps {
  onFilesChange: (files: UploadedFile[]) => void;
  accept?: string;
  multiple?: boolean;
  maxSize?: number; // in MB
  label?: string;
  helpText?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFilesChange,
  accept = '.pdf,.docx,.txt,.md',
  multiple = true,
  maxSize = 100,
  label,
  helpText = `Supported formats: ${accept} (max ${maxSize}MB per file)`,
}) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleFiles = (files: File[]) => {
    const newFiles: UploadedFile[] = files.map(file => ({
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'complete',
      progress: 100,
      file: file,
    }));

    const updatedFiles = [...uploadedFiles, ...newFiles];
    setUploadedFiles(updatedFiles);
    onFilesChange(updatedFiles);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const removeFile = (fileId: string) => {
    const updatedFiles = uploadedFiles.filter(file => file.id !== fileId);
    setUploadedFiles(updatedFiles);
    onFilesChange(updatedFiles);
  };

  return (
    <div>
      {label && (
        <label className="block text-sm font-medium text-gray-100 mb-3">{label}</label>
      )}

      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          dragActive
            ? 'border-blue-60 bg-blue-10'
            : 'border-gray-30 hover:border-blue-60'
        }`}
        onClick={() => document.getElementById('file-upload-input')?.click()}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <CloudArrowUpIcon className="w-12 h-12 text-gray-60 mx-auto mb-4" />
        <p className="text-gray-100 mb-2">Drag and drop files here</p>
        <p className="text-sm text-gray-70 mb-4">or click to select files</p>
        <input
          type="file"
          multiple={multiple}
          onChange={handleFileInput}
          accept={accept}
          className="hidden"
          id="file-upload-input"
        />
        <div className="btn-primary cursor-pointer inline-block">Select Files</div>
        <p className="text-xs text-gray-60 mt-3">{helpText}</p>
      </div>

      {/* File List */}
      {uploadedFiles.length > 0 && (
        <div className="mt-4 space-y-3">
          <h4 className="font-medium text-gray-100">
            Uploaded Files ({uploadedFiles.length})
          </h4>
          <div className="max-h-40 overflow-y-auto space-y-2">
            {uploadedFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center space-x-3 p-3 border border-gray-20 rounded-lg"
              >
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
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(file.id);
                    }}
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
  );
};

export default FileUpload;
