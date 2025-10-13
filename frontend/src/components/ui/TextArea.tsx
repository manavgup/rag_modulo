import React from 'react';

export interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helpText?: string;
  fullWidth?: boolean;
}

const TextArea = React.forwardRef<HTMLTextAreaElement, TextAreaProps>(
  (
    { label, error, helpText, fullWidth = false, className = '', id, ...props },
    ref
  ) => {
    const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;

    // Base textarea classes
    const baseClasses =
      'border rounded-md px-3 py-2 focus:outline-none focus:ring-2 transition-colors duration-200 resize-vertical';

    // State classes
    const stateClasses = error
      ? 'border-red-50 focus:ring-red-50 focus:border-red-50'
      : 'border-gray-40 focus:ring-blue-60 focus:border-blue-60';

    // Width class
    const widthClass = fullWidth ? 'w-full' : '';

    // Disabled classes
    const disabledClasses = props.disabled
      ? 'bg-gray-10 text-gray-50 cursor-not-allowed'
      : 'bg-white text-gray-100';

    const combinedClasses = `${baseClasses} ${stateClasses} ${widthClass} ${disabledClasses} ${className}`;

    return (
      <div className={fullWidth ? 'w-full' : ''}>
        {label && (
          <label
            htmlFor={textareaId}
            className="block text-sm font-medium text-gray-100 mb-2"
          >
            {label}
          </label>
        )}
        <textarea ref={ref} id={textareaId} className={combinedClasses} {...props} />
        {error && <p className="mt-1 text-sm text-red-50">{error}</p>}
        {helpText && !error && <p className="mt-1 text-sm text-gray-60">{helpText}</p>}
      </div>
    );
  }
);

TextArea.displayName = 'TextArea';

export default TextArea;
