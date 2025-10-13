import React from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
  children?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      icon,
      iconPosition = 'left',
      fullWidth = false,
      children,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    // Base classes
    const baseClasses =
      'inline-flex items-center justify-center font-medium rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2';

    // Variant classes
    const variantClasses = {
      primary:
        'bg-blue-60 hover:bg-blue-70 text-white focus:ring-blue-60 disabled:bg-gray-30 disabled:text-gray-60 disabled:cursor-not-allowed',
      secondary:
        'bg-gray-20 hover:bg-gray-30 text-gray-100 focus:ring-gray-60 disabled:bg-gray-10 disabled:text-gray-50 disabled:cursor-not-allowed',
      ghost:
        'text-gray-70 hover:text-gray-100 hover:bg-gray-20 focus:ring-gray-60 disabled:text-gray-50 disabled:cursor-not-allowed',
      danger:
        'bg-red-50 hover:bg-red-60 text-white focus:ring-red-50 disabled:bg-gray-30 disabled:text-gray-60 disabled:cursor-not-allowed',
    };

    // Size classes
    const sizeClasses = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg',
    };

    // Icon size classes
    const iconSizeClasses = {
      sm: 'w-4 h-4',
      md: 'w-5 h-5',
      lg: 'w-6 h-6',
    };

    // Width class
    const widthClass = fullWidth ? 'w-full' : '';

    // Combine all classes
    const combinedClasses = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${widthClass} ${className}`;

    // Loading spinner
    const LoadingSpinner = () => (
      <div
        className={`animate-spin rounded-full border-b-2 ${iconSizeClasses[size]} ${variant === 'ghost' || variant === 'secondary' ? 'border-gray-100' : 'border-white'}`}
        role="status"
        aria-label="Loading"
      />
    );

    return (
      <button
        ref={ref}
        className={combinedClasses}
        disabled={disabled || loading}
        aria-busy={loading}
        {...props}
      >
        {loading ? (
          <>
            <LoadingSpinner />
            {children && <span className="ml-2">{children}</span>}
          </>
        ) : (
          <>
            {icon && iconPosition === 'left' && <span className="mr-2">{icon}</span>}
            {children}
            {icon && iconPosition === 'right' && <span className="ml-2">{icon}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
