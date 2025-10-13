import React, { useId } from 'react';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helpText?: string;
  options: SelectOption[];
  fullWidth?: boolean;
  placeholder?: string;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      label,
      error,
      helpText,
      options,
      fullWidth = false,
      placeholder,
      className = '',
      id,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const selectId = id || generatedId;

    // Base select classes
    const baseClasses =
      'border rounded-md px-3 py-2 focus:outline-none focus:ring-2 transition-colors duration-200 appearance-none bg-no-repeat';

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
            htmlFor={selectId}
            className="block text-sm font-medium text-gray-100 mb-2"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <select ref={ref} id={selectId} className={combinedClasses} {...props}>
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-70">
            <svg
              className="fill-current h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
            >
              <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
            </svg>
          </div>
        </div>
        {error && <p className="mt-1 text-sm text-red-50">{error}</p>}
        {helpText && !error && <p className="mt-1 text-sm text-gray-60">{helpText}</p>}
      </div>
    );
  }
);

Select.displayName = 'Select';

export default Select;
