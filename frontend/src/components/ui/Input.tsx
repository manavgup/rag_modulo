import React, { useId } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helpText?: string;
  icon?: React.ReactNode;
  fullWidth?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    { label, error, helpText, icon, fullWidth = false, className = '', id, ...props },
    ref
  ) => {
    const generatedId = useId();
    const inputId = id || generatedId;

    // Base input classes
    const baseClasses =
      'border rounded-md px-3 py-2 focus:outline-none focus:ring-2 transition-colors duration-200';

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

    // Icon padding
    const iconClass = icon ? 'pl-10' : '';

    const combinedClasses = `${baseClasses} ${stateClasses} ${widthClass} ${disabledClasses} ${iconClass} ${className}`;

    return (
      <div className={fullWidth ? 'w-full' : ''}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-gray-100 mb-2"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              {icon}
            </div>
          )}
          <input ref={ref} id={inputId} className={combinedClasses} {...props} />
        </div>
        {error && <p className="mt-1 text-sm text-red-50">{error}</p>}
        {helpText && !error && <p className="mt-1 text-sm text-gray-60">{helpText}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
