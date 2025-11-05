import React from 'react';

export interface SimpleSelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: string;
  fullWidth?: boolean;
}

const SimpleSelect = React.forwardRef<HTMLSelectElement, SimpleSelectProps>(
  ({ error, fullWidth = false, className = '', children, ...props }, ref) => {
    // Base select classes
    const baseClasses =
      'border rounded-md px-3 py-2 focus:outline-none focus:ring-2 transition-colors duration-200 appearance-none bg-no-repeat';

    // State classes
    const stateClasses = error
      ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
      : 'border-gray-300 focus:ring-blue-600 focus:border-blue-600';

    // Width class
    const widthClass = fullWidth ? 'w-full' : '';

    // Disabled classes
    const disabledClasses = props.disabled
      ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
      : 'bg-white text-gray-900';

    const combinedClasses = `${baseClasses} ${stateClasses} ${widthClass} ${disabledClasses} ${className}`;

    return (
      <div className={fullWidth ? 'w-full' : ''}>
        <div className="relative">
          <select ref={ref} className={combinedClasses} {...props}>
            {children}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
            <svg
              className="fill-current h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
            >
              <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
            </svg>
          </div>
        </div>
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
      </div>
    );
  }
);

SimpleSelect.displayName = 'SimpleSelect';

export default SimpleSelect;
